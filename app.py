from flask import Flask, render_template, request, send_file
import simplekml
import math
import os

app = Flask(__name__)

def dms_to_decimal(deg, min_, sec):
    return float(deg) + float(min_) / 60 + float(sec) / 3600

def destination_point(lat, lon, bearing_deg, distance_m):
    R = 6371000  # Earth radius in meters
    bearing = math.radians(float(bearing_deg))
    lat1 = math.radians(float(lat))
    lon1 = math.radians(float(lon))
    d_div_r = float(distance_m) / R

    lat2 = math.asin(math.sin(lat1)*math.cos(d_div_r) +
                     math.cos(lat1)*math.sin(d_div_r)*math.cos(bearing))
    lon2 = lon1 + math.atan2(math.sin(bearing)*math.sin(d_div_r)*math.cos(lat1),
                             math.cos(d_div_r)-math.sin(lat1)*math.sin(lat2))

    return math.degrees(lat2), math.degrees(lon2)

@app.route('/')
def index():
    return render_template('form.html')

@app.route('/generate', methods=['POST'])
def generate():
    # Decimal input
    lat = request.form.get('latitude')
    lng = request.form.get('longitude')

    # If decimal input is not provided, use DMS
    if not lat or not lng:
        lat = dms_to_decimal(
            request.form.get('lat_deg'),
            request.form.get('lat_min'),
            request.form.get('lat_sec')
        )
        lng = dms_to_decimal(
            request.form.get('lng_deg'),
            request.form.get('lng_min'),
            request.form.get('lng_sec')
        )

    kml = simplekml.Kml()

    # Line from bearing and length
    if request.form.get('line_bearing') and request.form.get('line_length'):
        end_lat, end_lng = destination_point(lat, lng,
                                             request.form.get('line_bearing'),
                                             request.form.get('line_length'))
        linestring = kml.newlinestring(name="Line from Reference Point")
        linestring.coords = [(float(lng), float(lat)), (end_lng, end_lat)]
        linestring.style.linestyle.color = simplekml.Color.red
        linestring.style.linestyle.width = 3

    # Multiple lines every 15 degrees from user-defined starting bearing
    if request.form.get('multi_line_length') and request.form.get('start_bearing'):
        try:
            start_bearing = int(request.form.get('start_bearing')) % 360
            for i in range(0, 360, 15):
                bearing = (start_bearing + i) % 360
                end_lat, end_lng = destination_point(lat, lng, bearing, request.form.get('multi_line_length'))
                line = kml.newlinestring(name=f"Line {bearing}°")
                line.coords = [(float(lng), float(lat)), (end_lng, end_lat)]
                line.style.linestyle.color = simplekml.Color.blue
                line.style.linestyle.width = 2
        except ValueError:
            pass

    # Draw a circle
    if request.form.get('circle_radius'):
        radius = float(request.form.get('circle_radius'))
        num_points = 72  # 5 degree resolution
        coords = []
        for angle in range(0, 360, int(360 / num_points)):
            point_lat, point_lng = destination_point(lat, lng, angle, radius)
            coords.append((point_lng, point_lat))
        coords.append(coords[0])  # Close the circle
        pol = kml.newpolygon(name="Circle")
        pol.outerboundaryis = coords
        pol.style.polystyle.color = simplekml.Color.changealphaint(100, simplekml.Color.green)
        pol.style.linestyle.color = simplekml.Color.green
        pol.style.linestyle.width = 2

    # Draw 2D curved field of view from equipment
    if request.form.get('fov_angle') and request.form.get('fov_length') and request.form.get('fov_start_bearing'):
        try:
            fov_center = float(request.form.get('fov_start_bearing'))
            fov_half = float(request.form.get('fov_angle')) / 2
            fov_length = float(request.form.get('fov_length'))

            coords = [(float(lng), float(lat))]
            for angle in range(int(fov_center - fov_half), int(fov_center + fov_half) + 1, 1):
                a = angle % 360
                point_lat, point_lng = destination_point(lat, lng, a, fov_length)
                coords.append((point_lng, point_lat))
            coords.append((float(lng), float(lat)))  # Close the shape

            fov_poly = kml.newpolygon(name="2D Curved Field of View")
            fov_poly.outerboundaryis = coords
            fov_poly.style.polystyle.color = simplekml.Color.changealphaint(100, simplekml.Color.red)
            fov_poly.style.linestyle.color = simplekml.Color.red
            fov_poly.style.linestyle.width = 2
        except ValueError:
            pass

    output_name = request.form.get('filename') or "output"
    output_path = f"{output_name}.kml"
    kml.save(output_path)

    return send_file(output_path, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)
