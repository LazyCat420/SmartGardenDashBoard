from backend.main import app, db
from backend.models import CameraEndpoint
from backend.camera_service import test_connection

with app.app_context():
    endpoints = CameraEndpoint.query.all()
    print(f"Found {len(endpoints)} camera endpoints in DB:")
    for ep in endpoints:
        print(f"[{ep.id}] {ep.name} @ {ep.ssh_user}@{ep.ssh_host}:{ep.ssh_port}")
        res = test_connection(ep.ssh_host, ep.ssh_user, ep.ssh_port)
        print(f"  Connection: {'✅ REACHABLE' if res['reachable'] else '❌ FAILED'} - {res['message']}")
