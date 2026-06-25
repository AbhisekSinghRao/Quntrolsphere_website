import datetime
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from fastapi import FastAPI, Request, Form, File, UploadFile, Response, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

# Slowapi modules for DDoS and spam protection
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# Initialize Rate Limiter using client remote IP addresses
limiter = Limiter(key_func=get_remote_address)
app = FastAPI()
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# --- SECURE CONFIGURATION VIA INFRASTRUCTURE ENVIRONMENT VARIABLES ---
# Default targets fallback safely, but passwords must be pulled dynamically from Render env fields.
SMTP_SERVER = os.environ.get("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", 465))
COMPANY_INBOX = os.environ.get("COMPANY_INBOX", "contact@quntrolsphere.com")
EMAIL_PASSWORD = os.environ.get("EMAIL_PASSWORD") # Kept empty locally; populated securely inside Render

# Mount static files (images, css, brochures)
app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")


def get_current_year():
    """Returns the current string year safely passed into footer rendering variables."""
    return str(datetime.datetime.now(datetime.timezone.utc).year)


# Centralized Hardware and IP core database matching templates
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
    },
    "qkd-node": {
        "name": "Industrial QKD Deployment Node",
        "description": "Enterprise-grade hardware architecture designed for multi-topology quantum key distribution and secure infrastructure provisioning.",
        "images": ["qkd_node.png", "qkd_node_rear.png"],
        "brochure": "QKD_Node_Industrial_Specifications.pdf",
        "features": ["Multi-topology support (linear, mesh, star)", "Fibre-based hardware core infrastructure", "Quantum-classical network orchestration layer"]
    }
}


# --- HTTP INJECTION PROTECTION SECURITY MIDDLEWARE ---
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    # Mitigate Clickjacking hijacking attacks
    response.headers["X-Frame-Options"] = "DENY"
    # Mitigate reflective Cross-Site Scripting (XSS)
    response.headers["X-XSS-Protection"] = "1; mode=block"
    # Force strict browser respect for file types to block MIME-sniffing exploits
    response.headers["X-Content-Type-Options"] = "nosniff"
    # Scope tracking references shared externally
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response


# --- REUSABLE SECURE SMTP DISPATCHER ---
def send_automated_email(subject: str, html_body: str, to_email: str, reply_to_email: str = None):
    """Establishes safe TLS connections and handles transactional body delivery."""
    if not EMAIL_PASSWORD:
        print("[WARNING] Outbound SMTP configuration skipped. EMAIL_PASSWORD environment variable is unset.")
        return

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


# --- APPLICATION ROUTING INFRASTRUCTURE ---

@app.head("/")
async def home_head():
    return Response(status_code=200)

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse(request, "index.html", {"current_year": get_current_year()})

@app.get("/about", response_class=HTMLResponse)
async def about(request: Request):
    return templates.TemplateResponse(request, "about.html", {"current_year": get_current_year()})

@app.get("/services", response_class=HTMLResponse)
async def services(request: Request):
    return templates.TemplateResponse(request, "services.html", {"current_year": get_current_year()})

@app.get("/contact", response_class=HTMLResponse)
async def contact_page(request: Request):
    return templates.TemplateResponse(request, "contact.html", {"current_year": get_current_year()})


@app.post("/contact")
@limiter.limit("5/minute")  # Mitigates automated form submission spamming
async def handle_contact(
    request: Request, 
    name: str = Form(...), 
    email: str = Form(...), 
    company: str = Form(None), 
    message: str = Form(...)
):
    try:
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
@limiter.limit("5/minute")
async def handle_quote(
    request: Request,
    product: str = Form(...),
    name: str = Form(...),
    email: str = Form(...),
    organization: str = Form(...)
):
    try:
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
    
    return templates.TemplateResponse(request, "product.html", {"product": product, "current_year": get_current_year()})


@app.get("/thanks", response_class=HTMLResponse)
async def thanks(request: Request):
    return templates.TemplateResponse(request, "thanks.html", {"current_year": get_current_year()})


@app.post("/apply")
@limiter.limit("3/minute")
async def handle_application(
    request: Request,  # Required variable argument context infrastructure for slowapi evaluation tracking
    job_title: str = Form(...),
    name: str = Form(...),
    email: str = Form(...),
    education: str = Form(...),
    summary: str = Form(...),
    resume: UploadFile = File(...)
):
    try:
        # 1. STRICT FILE TYPE VALIDATION BLOCK (Blocks malicious script injection payloads)
        allowed_extensions = [".pdf", ".docx"]
        file_ext = os.path.splitext(resume.filename)[1].lower()
        if file_ext not in allowed_extensions:
            raise HTTPException(status_code=400, detail="Forbidden file layout structural extension. Only PDF and DOCX formats allowed.")

        # 2. STRICT FILE SIZE RESTRICTION BLOCK (Prevents server memory crash allocation exhaustion)
        MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 Megabytes absolute execution boundary limit
        file_content = await resume.read()
        if len(file_content) > MAX_FILE_SIZE:
            raise HTTPException(status_code=400, detail="Payload validation threshold broken. Attachment size exceeds 5MB limit.")

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

        # Prepare secure file configuration container mapping structural values safely
        part = MIMEBase('application', 'octet-stream')
        part.set_payload(file_content)
        encoders.encode_base64(part)
        
        clean_filename = f"Resume_{name.replace(' ', '_')}{file_ext}"
        part.add_header('Content-Disposition', f'attachment; filename="{clean_filename}"')
        msg.attach(part)

        if EMAIL_PASSWORD:
            with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
                server.starttls()
                server.login(COMPANY_INBOX, EMAIL_PASSWORD)
                server.send_message(msg)
        else:
            print("[WARNING] Careers transmission skipped. EMAIL_PASSWORD environment variable is missing.")

    except HTTPException as http_err:
        # Re-raise explicit HTTP errors to prevent catching framework responses inside the general tracker block
        raise http_err
    except Exception as e:
        print(f"SMTP Transmission failure encountered: {e}")

    return RedirectResponse(url="/thanks", status_code=303)


if __name__ == "__main__":
    import uvicorn
    prod_port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=prod_port)