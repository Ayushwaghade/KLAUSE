const request = require('supertest');
const app = require('./app');

describe('GET /weather', () => {
  it('should return 200 and weather data for valid coordinates', async () => {
    const response = await request(app).get('/weather?lat=52.52&lon=13.41');
    expect(response.status).toBe(200);
    expect(response.body).toHaveProperty('current');
  });

  it('should return 400 for missing coordinates', async () => {
    const response = await request(app).get('/weather');
    expect(response.status).toBe(400);
  });
});