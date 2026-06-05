"""
Email Viewer Component for rendering EML files as HTML
"""

import email
from email.mime.text import MIMEText
from typing import Optional
import re


class EmailViewer:
    """Display EML files as they would appear in an email client"""
    
    def __init__(self, file_path: Optional[str] = None, file_content: Optional[bytes] = None):
        if file_path:
            with open(file_path, 'rb') as f:
                self.message = email.message_from_binary_file(f)
        elif file_content:
            self.message = email.message_from_bytes(file_content)
        else:
            raise ValueError("Either file_path or file_content must be provided")
    
    def get_headers_html(self) -> str:
        """Generate HTML for email headers"""
        subject = self.message.get('Subject', '(No Subject)')
        from_addr = self.message.get('From', 'Unknown')
        to_addr = self.message.get('To', 'Unknown')
        date = self.message.get('Date', 'Unknown')
        cc = self.message.get('Cc', '')
        
        html = f"""
        <div style="border-bottom: 1px solid #ccc; padding-bottom: 10px; margin-bottom: 15px; background-color: #f9f9f9; padding: 15px; border-radius: 5px;">
            <div style="margin-bottom: 10px;">
                <strong style="color: #333; font-size: 16px;">From:</strong> 
                <span>{from_addr}</span>
            </div>
            <div style="margin-bottom: 10px;">
                <strong style="color: #333;">To:</strong> 
                <span>{to_addr}</span>
            </div>
            {f'<div style="margin-bottom: 10px;"><strong style="color: #333;">Cc:</strong> <span>{cc}</span></div>' if cc else ''}
            <div style="margin-bottom: 10px;">
                <strong style="color: #333;">Date:</strong> 
                <span>{date}</span>
            </div>
            <div style="margin-top: 15px;">
                <strong style="color: #1f77b4; font-size: 18px;">Subject:</strong> 
                <span style="font-size: 18px;">{subject}</span>
            </div>
        </div>
        """
        return html
    
    def get_body_html(self) -> str:
        """Extract and return HTML body from email"""
        html_body = None
        text_body = None
        
        if self.message.is_multipart():
            for part in self.message.walk():
                content_type = part.get_content_type()
                
                if content_type == 'text/html':
                    try:
                        payload = part.get_payload(decode=True)
                        charset = part.get_content_charset() or 'utf-8'
                        html_body = payload.decode(charset, errors='replace')
                    except:
                        pass
                
                elif content_type == 'text/plain' and not text_body:
                    try:
                        payload = part.get_payload(decode=True)
                        charset = part.get_content_charset() or 'utf-8'
                        text_body = payload.decode(charset, errors='replace')
                    except:
                        pass
        else:
            if self.message.get_content_type() == 'text/html':
                try:
                    payload = self.message.get_payload(decode=True)
                    charset = self.message.get_content_charset() or 'utf-8'
                    html_body = payload.decode(charset, errors='replace')
                except:
                    pass
            elif self.message.get_content_type() == 'text/plain':
                try:
                    payload = self.message.get_payload(decode=True)
                    charset = self.message.get_content_charset() or 'utf-8'
                    text_body = payload.decode(charset, errors='replace')
                except:
                    pass
        
        # Use HTML if available, otherwise convert text to HTML
        if html_body:
            return html_body
        elif text_body:
            # Convert plain text to HTML
            text_body = text_body.replace("&", "&amp;")
            text_body = text_body.replace("<", "&lt;")
            text_body = text_body.replace(">", "&gt;")
            text_body = text_body.replace("\n", "<br>")
            return f"<pre style='font-family: Arial, sans-serif; white-space: pre-wrap;'>{text_body}</pre>"
        
        return "<p>No content available</p>"
    
    def get_full_html(self) -> str:
        """Get complete HTML representation of email"""
        headers_html = self.get_headers_html()
        body_html = self.get_body_html()
        
        full_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{
                    font-family: Arial, Helvetica, sans-serif;
                    margin: 0;
                    padding: 0;
                    background-color: #f0f0f0;
                }}
                .email-container {{
                    max-width: 800px;
                    margin: 20px auto;
                    background-color: white;
                    padding: 0;
                    border: 1px solid #ddd;
                    border-radius: 5px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                }}
                .email-headers {{
                    padding: 20px;
                }}
                .email-body {{
                    padding: 20px;
                    color: #333;
                    line-height: 1.6;
                }}
                img {{
                    max-width: 100%;
                    height: auto;
                }}
            </style>
        </head>
        <body>
            <div class="email-container">
                <div class="email-headers">
                    {headers_html}
                </div>
                <div class="email-body">
                    {body_html}
                </div>
            </div>
        </body>
        </html>
        """
        return full_html
    
    def get_attachments_info(self) -> list:
        """Get information about attachments"""
        attachments = []
        if self.message.is_multipart():
            for part in self.message.walk():
                if part.get_content_disposition() == 'attachment':
                    filename = part.get_filename()
                    if filename:
                        content_type = part.get_content_type()
                        size = len(part.get_payload(decode=True))
                        attachments.append({
                            'filename': filename,
                            'content_type': content_type,
                            'size': size
                        })
        return attachments
