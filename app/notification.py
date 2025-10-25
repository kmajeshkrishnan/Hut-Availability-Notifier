import resend
from .config import settings
from datetime import date

resend.api_key = settings.resend_api_key

html_template = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Hut Availability Alert</title>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: #333;
            margin: 0;
            padding: 0;
            background-color: #f8f9fa;
        }
        .container {
            max-width: 600px;
            margin: 0 auto;
            background: #ffffff;
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            border: 1px solid #e9ecef;
        }
        .header {
            background: linear-gradient(135deg, #10b981 0%, #059669 100%);
            color: white;
            padding: 30px 20px;
            text-align: center;
        }
        .header h1 {
            margin: 0;
            font-size: 28px;
            font-weight: 600;
        }
        .header .subtitle {
            margin: 10px 0 0 0;
            font-size: 16px;
            opacity: 0.9;
        }
        .content {
            padding: 30px;
        }
        .alert-badge {
            background: #dcfce7;
            color: #166534;
            padding: 8px 16px;
            border-radius: 20px;
            font-weight: 600;
            font-size: 14px;
            display: inline-block;
            margin-bottom: 20px;
            border: 1px solid #bbf7d0;
        }
        .hut-details {
            background: #f8f9fa;
            padding: 20px;
            border-radius: 8px;
            margin: 20px 0;
            border-left: 4px solid #10b981;
        }
        .detail-row {
            display: flex;
            justify-content: space-between;
            margin: 8px 0;
            padding: 8px 0;
            border-bottom: 1px solid #e9ecef;
        }
        .detail-row:last-child {
            border-bottom: none;
        }
        .detail-label {
            font-weight: 600;
            color: #6b7280;
        }
        .detail-value {
            font-weight: 500;
            color: #1f2937;
        }
        .cta-button {
            display: inline-block;
            background: linear-gradient(135deg, #10b981 0%, #059669 100%);
            color: white;
            padding: 14px 32px;
            text-decoration: none;
            border-radius: 8px;
            font-weight: 600;
            font-size: 16px;
            margin: 25px 0;
            text-align: center;
            transition: transform 0.2s;
        }
        .cta-button:hover {
            transform: translateY(-2px);
        }
        .urgency-note {
            background: #fef3c7;
            border: 1px solid #fcd34d;
            color: #92400e;
            padding: 15px;
            border-radius: 8px;
            margin: 20px 0;
            text-align: center;
            font-weight: 500;
        }
        .footer {
            background: #f8f9fa;
            padding: 20px;
            text-align: center;
            color: #6b7280;
            font-size: 14px;
            border-top: 1px solid #e9ecef;
        }
        .disclaimer {
            font-size: 12px;
            color: #9ca3af;
            margin-top: 15px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🏔️ Hut Available!</h1>
            <p class="subtitle">Notification Service - a hut has become available!</p>
        </div>
        
        <div class="content">
            <div class="alert-badge">✅ AVAILABLE NOW</div>
            
            <h2 style="margin-top: 0; color: #1f2937;">Booking Opportunity</h2>
            <p style="color: #6b7280; margin-bottom: 25px;">Opfinger Hut is now available for booking. Act quickly as these spots fill up fast!</p>

            <div class="hut-details">
                <div class="detail-row">
                    <span class="detail-label">Hut Name:</span>
                    <span class="detail-value">[[HUT_NAME]]</span>
                </div>
                <div class="detail-row">
                    <span class="detail-label">Location:</span>
                    <span class="detail-value">[[HUT_LOCATION]]</span>
                </div>
                <div class="detail-row">
                    <span class="detail-label">Available Date:</span>
                    <span class="detail-value">[[DATE_RANGE]]</span>
                </div>
            </div>

            <div class="urgency-note">
                ⚡ This availability was just detected. Other people may be looking at the same dates!
            </div>

            <div style="text-align: center;">
                <a href="[[BOOKING_URL]]" class="cta-button">Book Now →</a>
            </div>

            <p style="text-align: center; color: #6b7280; margin-bottom: 0;">
                This alert was sent because you requested notifications for [[HUT_NAME]] availability.
            </p>
        </div>
        
        <div class="footer">
            <p>DLOK Events</p>
            <p>Dev: kmajeshkrishnan</p>
            <div class="disclaimer">
                You received this email because you subscribed to hut availability alerts.
            </div>
        </div>
    </div>
</body>
</html>
"""

# Function to send the hut availability email
def send_hut_availability_email(day: date):

    to_email = "ajeshkrishnankm@gmail.com"
    hut_details = {
    'name': 'Opfinger Hut',
    'location': 'Near Opfinger See, Freiburg im Breisgau',
    'date_range': day.strftime('%A, %b %d, %Y'),
    'booking_url': 'https://www.forsthuetten-freiburg.de/de/buchen/index.php?id=3',
    }

    # Replace placeholders with actual data
    html_content = html_template.replace("[[HUT_NAME]]", hut_details['name'])
    html_content = html_content.replace("[[HUT_LOCATION]]", hut_details['location'])
    html_content = html_content.replace("[[DATE_RANGE]]", hut_details['date_range'])
    html_content = html_content.replace("[[BOOKING_URL]]", hut_details['booking_url'])
    
    r = resend.Emails.send({
        "from": "DLOK Hut Alerts <onboarding@resend.dev>",
        "to": to_email,
        "subject": f"🚨 Available: {hut_details['name']} - {hut_details['date_range']}",
        "html": html_content
    })
    return r