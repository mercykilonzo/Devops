"""Tests for Service B.

Uses SimpleTestCase (no database). Health tests prove the app boots; the
GreetFlow tests mock the downstream HTTP call so B's forward-to-C success and
error paths are exercised without needing C running.
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
        self.assertEqual(body['service'], 'service-b')
        self.assertIn(body['status'], ('ok', 'degraded'))  # PRD health contract

    def test_unknown_route_is_404(self):
        self.assertEqual(self.client.get('/does-not-exist').status_code, 404)


class GreetFlowTests(SimpleTestCase):
    @patch('api.views.request_json')
    def test_greet_forwards_success(self, mock_req):
        mock_req.return_value = {'status': 200, 'body': {'status': 'processed'}}
        resp = self.client.get('/greet')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()['status'], 'forwarded')
        mock_req.assert_called_once()  # B called downstream (C)

    @patch('api.views.request_json')
    def test_greet_downstream_failure_returns_502(self, mock_req):
        mock_req.side_effect = Exception('timeout')
        resp = self.client.get('/greet')
        self.assertEqual(resp.status_code, 502)
        self.assertEqual(resp.json()['status'], 'error')
