from django.test import TestCase, Client

class ServiceCHealthTest(TestCase):
    def setUp(self):
        self.client = Client()

    def test_health_returns_200(self):
        response = self.client.get('/health')
        self.assertEqual(response.status_code, 200)

    def test_health_returns_correct_service_name(self):
        response = self.client.get('/health')
        data = response.json()
        self.assertEqual(data['service'], 'service-c')
        self.assertEqual(data['status'], 'healthy')

    def test_health_returns_correct_port(self):
        response = self.client.get('/health')
        data = response.json()
        self.assertIn('port', data)
        self.assertIn('message', data)

    def test_unknown_route_returns_404(self):
        response = self.client.get('/unknown-route')
        self.assertEqual(response.status_code, 404)
