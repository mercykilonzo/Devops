"""Tests for Service C.

Uses SimpleTestCase (no database) since the health endpoint touches no models.
These run in CI via `python manage.py test` and block merge on failure.
"""

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
