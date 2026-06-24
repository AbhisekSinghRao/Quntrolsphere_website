import datetime
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from fastapi import FastAPI, Request, Form, File, UploadFile, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

app = FastAPI()

# Configuration variables for your enterprise mail server
SMTP_SERVER = "smtp.yourmailprovider.com"  # e.g., smtp.gmail.com or AWS SES endpoint
SMTP_PORT = 587
COMPANY_INBOX = "contact@quntrolsphere.com"
EMAIL_PASSWORD = "your-secure-app-password"  # Use environment variables in production!

# Mount static files (images, css, brochures)
app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")

# Fixed the deprecated utcnow call to use timezone-aware standard objects
def get_utc_now():
    return datetime.datetime.now(datetime.timezone.utc)

# FIXED: Replaced direct dictionary element writing with safe initialization update 
# to support Jinja2 template caching engine mechanics under Python 3.14+ safely.
templates.env.globals.update(now=get_utc_now)

# Mock Product Database matching your services.html paths
PRODUCTS = {
    "qcc-board": {
        "name": "QCC FPGA Development Board",
        "description": "Indigenous FPGA platform for quantum communication systems.",
        "images": ["qcc_board.jpeg","QCC_3.jpeg","QCC_2.jpeg"],
        "brochure": "qcc_board_brochure.pdf",
        "features": ["High-performance FPGA fabric", "Optimized for Quantum Communication", "High-speed data channels"]
    },
    "fmc-card": {
        "name": "Custom FPGA Mezzanine Card (FMC)",
        "description": "High-performance FPGA mezzanine module designed for Xilinx ZCU102.",
        "images": ["FMC.jpeg"], 
        "brochure": "fmc_card_brochure.pdf",
        "features": ["ZCU102 compatible", "Picosecond timing control", "QKD experimental interface"]
    },
    "merlin-ip": {
        "name": "MERLIN Synchronization IP",
        "description": "Clock synchronization technology with picosecond precision.",
        "images": ["MERLIN.jpeg"],
        "brochure": "merlin_brochure.pdf",
        "features": ["Picosecond-level timing alignment", "Geographically distributed system lock", "Resilient architecture"]
    },
    "qubit-primer": {
        "name": "QKD Networks Primer Kit",
        "description": "Hands-on educational platform for quantum key distribution experiments.",
        "images": ["primer_kit.jpeg", "qubit_primer.png"],
        "brochure": "qubit_primer_brochure.pdf",
        "features": ["Coherent-One Way protocol implementation", "Educational lab manuals included", "Plug-and-play optical modules"]
    },
    "pattern-generator-ip": {
        "name": "High Speed Pattern Generation IP Core",
        "description": "Programmable FPGA-based pattern generator supporting PRBS.",
        "images": ["pattern_gen.png"],
        "brochure": "pattern_gen_brochure.pdf",
        "features": ["Multi-Gb/s data rates supported", "PRBS & User-defined sequences", "Electro-optic testing companion"]
    }
}

# --- REUSABLE SECURE SMTP DISPATCHER ---
def send_automated_email(subject: str, html_body: str, to_email: str, reply_to_email: str = None):
    """Establishes safe TLS connections and handles transactional body delivery."""
    msg = MIMEMultipart("alternative")
    msg['From'] = COMPANY_INBOX
    msg['To'] = to_email
    msg['Subject'] = subject
    if reply_to_email:
        msg['Reply-To'] = reply_to_email

    msg.attach(MIMEText(html_body, 'html'))

    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
        server.starttls()
        server.login(COMPANY_INBOX, EMAIL_PASSWORD)
        server.send_message(msg)


# --- CORE APPLICATION ROUTING INFRASTRUCTURE ---

# FIXED: Explicit HEAD interceptor responding to root queries with an un-bodied 200 OK.
# Clears Render proxy routers from triggering 405 system deployment failure status metrics.
@app.head("/")
async def home_head():
    return Response(status_code=200)

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/about", response_class=HTMLResponse)
async def about(request: Request):
    return templates.TemplateResponse("about.html", {"request": request})

@app.get("/services", response_class=HTMLResponse)
async def services(request: Request):
    return templates.TemplateResponse("services.html", {"request": request})

@app.get("/contact", response_class=HTMLResponse)
async def contact_page(request: Request):
    return templates.TemplateResponse("contact.html", {"request": request})

@app.post("/contact")
async def handle_contact(
    request: Request, 
    name: str = Form(...), 
    email: str = Form(...), 
    company: str = Form(None), 
    message: str = Form(...)
):
    try:
        # 1. Internal Notification (Sent to your team)
        subject_internal = f"[CONTACT INQUIRY] - Technical Lead from {name}"
        html_internal = f"""
        <html>
          <body style="font-family: Arial, sans-serif; color: #333; line-height: 1.6;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #e2e8f0; border-radius: 8px;">
              <h2 style="color: #2563eb; border-bottom: 2px solid #e2e8f0; padding-bottom: 10px;">New Engineering Inquiry</h2>
              <table style="width: 100%; border-collapse: collapse; margin-top: 15px;">
                <tr><td style="padding: 6px 0; font-weight: bold; width: 30%;">Full Name:</td><td style="padding: 6px 0;">{name}</td></tr>
                <tr><td style="padding: 6px 0; font-weight: bold;">Email Address:</td><td style="padding: 6px 0;"><a href="mailto:{email}">{email}</a></td></tr>
                <tr><td style="padding: 6px 0; font-weight: bold;">Organization:</td><td style="padding: 6px 0;">{company if company else 'Not Specified'}</td></tr>
              </table>
              <h3 style="color: #475569; margin-top: 20px; border-bottom: 1px solid #edf2f7; padding-bottom: 5px;">Project Summary</h3>
              <p style="background-color: #f8fafc; padding: 12px; border-radius: 6px; color: #334155; white-space: pre-wrap;">{message}</p>
            </div>
          </body>
        </html>
        """
        send_automated_email(subject_internal, html_internal, to_email=COMPANY_INBOX, reply_to_email=email)

        # 2. Short Auto-Response (Sent directly to the client via clean utility helper method)
        subject_client = "Thank you for contacting QuntrolSphere"
        html_client = f"""
        <html>
          <body style="font-family: Arial, sans-serif; color: #333; line-height: 1.6; padding: 20px;">
            <div style="max-width: 500px; margin: 0 auto; padding: 20px; border: 1px solid #e2e8f0; border-radius: 8px;">
              <p>Dear {name},</p>
              <p>Thank you for your inquiry. We have successfully received your message and project specifications.</p>
              <p>Our engineering team is reviewing your requirements and will reach out to you shortly.</p>
              <br>
              <p style="font-size: 13px; color: #64748b; margin-top: 20px; border-top: 1px solid #e2e8f0; padding-top: 15px;">
                <strong>QuntrolSphere Technical Operations</strong><br>
                <a href="mailto:contact@quntrolsphere.com" style="color: #2563eb; text-decoration: none;">contact@quntrolsphere.com</a>
              </p>
            </div>
          </body>
        </html>
        """
        send_automated_email(subject_client, html_client, to_email=email)

    except Exception as e:
        print(f"SMTP Inquiry Interface Error: {e}")
        
    return RedirectResponse(url="/thanks", status_code=303)


@app.post("/request-quote")
async def handle_quote(
    request: Request,
    product: str = Form(...),
    name: str = Form(...),
    email: str = Form(...),
    organization: str = Form(...)
):
    try:
        # 1. Internal Notification (Sent to company inbox)
        subject_internal = f"[QUOTE REQUEST] - {product} - From {name}"
        html_internal = f"""
        <html>
          <body style="font-family: Arial, sans-serif; color: #333; line-height: 1.6;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #e2e8f0; border-radius: 8px;">
              <h2 style="color: #0d9488; border-bottom: 2px solid #e2e8f0; padding-bottom: 10px;">Commercial RFQ Quote Request</h2>
              <table style="width: 100%; border-collapse: collapse; margin-top: 15px;">
                <tr><td style="padding: 6px 0; font-weight: bold; width: 35%;">Target Hardware/IP:</td><td style="padding: 6px 0; color: #0d9488; font-weight: bold;">{product}</td></tr>
                <tr><td style="padding: 6px 0; font-weight: bold;">Requester Name:</td><td style="padding: 6px 0;">{name}</td></tr>
                <tr><td style="padding: 6px 0; font-weight: bold;">Email Address:</td><td style="padding: 6px 0;"><a href="mailto:{email}">{email}</a></td></tr>
                <tr><td style="padding: 6px 0; font-weight: bold;">Institution/Entity:</td><td style="padding: 6px 0;">{organization}</td></tr>
              </table>
            </div>
          </body>
        </html>
        """
        send_automated_email(subject_internal, html_internal, to_email=COMPANY_INBOX, reply_to_email=email)

        # 2. Short Auto-Response (Sent directly to the client via clean utility helper method)
        subject_client = f"Quote Request Received: {product}"
        html_client = f"""
        <html>
          <body style="font-family: Arial, sans-serif; color: #333; line-height: 1.6; padding: 20px;">
            <div style="max-width: 500px; margin: 0 auto; padding: 20px; border: 1px solid #e2e8f0; border-radius: 8px;">
              <p>Dear {name},</p>
              <p>Thank you for requesting a quote for the <strong>{product}</strong>.</p>
              <p>Our commercial team is preparing the documentation for <em>{organization}</em> and will reach out to you shortly.</p>
              <br>
              <p style="font-size: 13px; color: #64748b; margin-top: 20px; border-top: 1px solid #e2e8f0; padding-top: 15px;">
                <strong>QuntrolSphere Commercial Operations</strong><br>
                <a href="mailto:contact@quntrolsphere.com" style="color: #0d9488; text-decoration: none;">contact@quntrolsphere.com</a>
              </p>
            </div>
          </body>
        </html>
        """
        send_automated_email(subject_client, html_client, to_email=email)

    except Exception as e:
        print(f"SMTP RFQ Interface Error: {e}")
        
    return RedirectResponse(url="/thanks", status_code=303)


@app.get("/product/{product_id}", response_class=HTMLResponse)
async def product_page(request: Request, product_id: str):
    product = PRODUCTS.get(product_id)
    if not product:
        return HTMLResponse(content="Product Not Found", status_code=404)
    return templates.TemplateResponse("product.html", {"request": request, "product": product})


@app.get("/thanks", response_class=HTMLResponse)
async def thanks(request: Request):
    return templates.TemplateResponse("thanks.html", {"request": request})


@app.post("/apply")
async def handle_application(
    job_title: str = Form(...),
    name: str = Form(...),
    email: str = Form(...),
    education: str = Form(...),
    summary: str = Form(...),
    resume: UploadFile = File(...)
):
    try:
        msg = MIMEMultipart()
        msg['From'] = COMPANY_INBOX
        msg['To'] = COMPANY_INBOX
        msg['Subject'] = f"[CAREERS Application] - {job_title} - {name}"
        msg['Reply-To'] = email

        html_body = f"""
        <html>
          <body style="font-family: Arial, sans-serif; color: #333; line-height: 1.6;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #e2e8f0; border-radius: 8px;">
              <h2 style="color: #1e3a8a; border-bottom: 2px solid #e2e8f0; padding-bottom: 10px;">New Job Application Received</h2>
              <table style="width: 100%; border-collapse: collapse; margin-top: 15px;">
                <tr><td style="padding: 8px 0; font-weight: bold; width: 30%;">Target Role:</td><td style="padding: 8px 0; color: #2563eb; font-weight: bold;">{job_title}</td></tr>
                <tr><td style="padding: 8px 0; font-weight: bold;">Applicant Name:</td><td style="padding: 8px 0;">{name}</td></tr>
                <tr><td style="padding: 8px 0; font-weight: bold;">Email:</td><td style="padding: 8px 0;"><a href="mailto:{email}">{email}</a></td></tr>
                <tr><td style="padding: 8px 0; font-weight: bold;">Education:</td><td style="padding: 8px 0;">{education}</td></tr>
              </table>
              <h3 style="color: #475569; margin-top: 20px; border-bottom: 1px solid #edf2f7; padding-bottom: 5px;">Professional Summary</h3>
              <p style="background-color: #f8fafc; padding: 12px; border-radius: 6px; font-style: italic; color: #475569;">"{summary}"</p>
              <p style="font-size: 11px; color: #94a3b8; margin-top: 25px; text-align: center;">Automated notification secure dispatch via QuntrolSphere Gateway.</p>
            </div>
          </body>
        </html>
        """
        msg.attach(MIMEText(html_body, 'html'))

        file_content = await resume.read()
        part = MIMEBase('application', 'octet-stream')
        part.set_payload(file_content)
        encoders.encode_base64(part)
        
        clean_filename = f"Resume_{name.replace(' ', '_')}.pdf"
        part.add_header('Content-Disposition', f'attachment; filename="{clean_filename}"')
        msg.attach(part)

        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(COMPANY_INBOX, EMAIL_PASSWORD)
            server.send_message(msg)

    except Exception as e:
        print(f"SMTP Transmission failure encountered: {e}")

    return RedirectResponse(url="/thanks", status_code=303)


# FIXED: Added standard global network interface bind handler so if called directly,
# it automatically binds to 0.0.0.0 and grabs Render's allocated infrastructure port.
if __name__ == "__main__":
    import uvicorn
    prod_port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=prod_port)