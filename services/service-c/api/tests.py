"""Tests for Service C.

Uses SimpleTestCase (no database). Health tests prove the app boots; the
GreetFlow tests mock the callback HTTP call so C's process-and-call-back-A
success and error paths are exercised without needing A running.
These run in CI via `python manage.py test` and block merge on failure.
"""

from unittest.mock import patch

from django.test import SimpleTestCase


class HealthEndpointTests(SimpleTestCase):
    def test_health_returns_200(self):
        response = self.client.get('/health')
        self.assertEqual(response.status_code, 200)

    def test_health_reports_this_service(self):
        body = self.client.get('/health').json()
        self.assertEqual(body['service'], 'service-c')
        self.assertIn(body['status'], ('ok', 'degraded'))  # PRD health contract

    def test_unknown_route_is_404(self):
        self.assertEqual(self.client.get('/does-not-exist').status_code, 404)


class GreetFlowTests(SimpleTestCase):
    @patch('api.views.request_json')
    def test_greet_c_processes_and_calls_back(self, mock_req):
        mock_req.return_value = {'status': 200, 'body': {'status': 'received'}}
        resp = self.client.get('/greet-c')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()['status'], 'processed')
        mock_req.assert_called_once()  # C called back into A

    @patch('api.views.request_json')
    def test_greet_c_callback_failure_returns_500(self, mock_req):
        mock_req.side_effect = Exception('callback failed')
        resp = self.client.get('/greet-c')
        self.assertEqual(resp.status_code, 500)
        self.assertEqual(resp.json()['status'], 'error')
