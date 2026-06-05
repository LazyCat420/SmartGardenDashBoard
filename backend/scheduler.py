"""
Background Scheduler for Smart Garden Dashboard Capture Schedules.
Runs a background thread that polls for pending schedules, triggers captures,
and executes vision LLM analysis.
"""

import time
import threading
import logging
import os
import json
from datetime import datetime, timedelta

from backend.main import app, db, CaptureSchedule, CameraEndpoint, CameraCapture, Plant, GrowthLog, PestIssue
from backend.camera_service import capture_image as cam_capture_image
from backend.camera_service import analyze_image as cam_analyze_image

logger = logging.getLogger('smartgarden.scheduler')

def run_pending_schedules():
    """Find and run all pending active capture schedules."""
    now = datetime.utcnow()
    # Find active schedules whose next_run is in the past (or is None)
    schedules = CaptureSchedule.query.filter(
        CaptureSchedule.is_active == True,
        (CaptureSchedule.next_run == None) | (CaptureSchedule.next_run <= now)
    ).all()

    if not schedules:
        return

    logger.info(f"Found {len(schedules)} pending capture schedule(s)")

    for schedule in schedules:
        logger.info(f"Running scheduled capture for schedule ID {schedule.id} (endpoint ID {schedule.endpoint_id})")
        endpoint = CameraEndpoint.query.get(schedule.endpoint_id)
        if not endpoint or not endpoint.is_active:
            logger.warning(f"Endpoint ID {schedule.endpoint_id} not found or inactive, skipping.")
            # Reschedule to prevent infinite loop / retries
            interval = schedule.interval_minutes or 360
            schedule.next_run = now + timedelta(minutes=interval)
            db.session.commit()
            continue

        # Get plant context
        plant_name = None
        plant_variety = None
        last_height = None
        if schedule.plant_id:
            plant = Plant.query.get(schedule.plant_id)
            if plant:
                plant_name = plant.display_name
                plant_variety = plant.variety
                last_log = GrowthLog.query.filter_by(plant_id=plant.id)\
                    .order_by(GrowthLog.date.desc()).first()
                if last_log and last_log.height_cm:
                    last_height = last_log.height_cm

        # 1. Trigger SSH capture
        capture_result = cam_capture_image(
            ssh_host=endpoint.ssh_host,
            ssh_user=endpoint.ssh_user,
            ssh_port=endpoint.ssh_port,
            capture_command=endpoint.capture_command,
            endpoint_id=endpoint.id
        )

        # Update schedule timing
        interval = schedule.interval_minutes or 360
        schedule.last_run = now
        schedule.next_run = now + timedelta(minutes=interval)
        db.session.commit()

        if not capture_result['success']:
            logger.error(f"Scheduled capture failed for schedule ID {schedule.id}: {capture_result['message']}")
            continue

        # 2. Save capture to database
        capture = CameraCapture(
            endpoint_id=endpoint.id,
            plant_id=schedule.plant_id,
            filename=capture_result['filename'],
            capture_type='scheduled',
            analysis_status='pending'
        )
        db.session.add(capture)
        endpoint.last_seen = now
        db.session.commit()

        logger.info(f"Scheduled capture saved as ID {capture.id}. Triggering vision analysis...")

        # 3. Trigger vision analysis
        captures_dir = os.environ.get('CAPTURES_DIR', '/app/captures')
        safe_filename = os.path.basename(capture.filename)
        image_path = os.path.join(captures_dir, safe_filename + ".jpg")
        depth_path = os.path.join(captures_dir, safe_filename + "_depth.npy")

        capture.analysis_status = 'analyzing'
        db.session.commit()

        analysis_result = cam_analyze_image(
            image_path=image_path,
            plant_name=plant_name,
            plant_variety=plant_variety,
            last_height=last_height,
            rotation=endpoint.rotation if endpoint else 0,
            hflip=endpoint.hflip if endpoint else False,
            vflip=endpoint.vflip if endpoint else False,
            depth_path=depth_path
        )

        if analysis_result['success']:
            capture.analysis_status = 'complete'
            capture.analysis_result = json.dumps(analysis_result['analysis'])
            capture.analyzed_at = datetime.utcnow()
            db.session.commit()

            # Auto-create growth log
            analysis = analysis_result['analysis']
            if capture.plant_id and analysis.get('estimated_height_cm'):
                growth = GrowthLog(
                    plant_id=capture.plant_id,
                    date=capture.captured_at,
                    height_cm=analysis.get('estimated_height_cm'),
                    width_cm=analysis.get('estimated_width_cm'),
                    health_rating=analysis.get('health_rating'),
                    notes=f"Auto-logged from scheduled camera analysis: {analysis.get('health_notes', '')}",
                    image_url=f'/api/camera/captures/{capture.id}/image'
                )
                db.session.add(growth)

            # Auto-create pest issues
            if capture.plant_id and analysis.get('pests_detected'):
                for pest in analysis['pests_detected']:
                    if pest.get('type'):
                        pest_issue = PestIssue(
                            plant_id=capture.plant_id,
                            date_identified=capture.captured_at,
                            pest_type=pest['type'][:100],
                            severity=pest.get('severity', 'moderate'),
                            notes=f"Detected via scheduled camera analysis (capture #{capture.id})"
                        )
                        db.session.add(pest_issue)

            db.session.commit()
            logger.info(f"Scheduled analysis complete for capture ID {capture.id}")
        else:
            capture.analysis_status = 'failed'
            db.session.commit()
            logger.error(f"Scheduled analysis failed for capture ID {capture.id}: {analysis_result.get('error', 'Unknown error')}")

def scheduler_loop():
    """Main scheduler loop."""
    logger.info("Scheduler thread started. Sleeping 10s before first run...")
    time.sleep(10)  # Wait for DB tables to be fully created/initialized
    
    while True:
        try:
            with app.app_context():
                run_pending_schedules()
        except Exception as e:
            logger.error(f"Error in scheduler loop: {e}", exc_info=True)
        # Sleep for 30 seconds between checks
        time.sleep(30)

def start_scheduler():
    """Start the background scheduler in a daemon thread."""
    thread = threading.Thread(target=scheduler_loop, name="SmartGardenScheduler", daemon=True)
    thread.start()
    logger.info("Background scheduler thread spawned.")
