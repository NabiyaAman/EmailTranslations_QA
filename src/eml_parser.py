"""
EML file parser for extracting email content and metadata.
"""
import email
from typing import Dict, List, Optional


class EMLParser:
    """Parse EML files and extract structured email content."""

    def __init__(self, file_path: Optional[str] = None, file_content: Optional[bytes] = None):
        self.message = None
        if file_path:
            with open(file_path, 'rb') as f:
                self.message = email.message_from_binary_file(f)
        elif file_content:
            self.message = email.message_from_bytes(file_content)
        else:
            raise ValueError("Either file_path or file_content must be provided")

    def get_headers(self) -> Dict[str, str]:
        """Extract common email headers."""
        return {
            'subject': self.message.get('Subject', ''),
            'from': self.message.get('From', ''),
            'to': self.message.get('To', ''),
            'cc': self.message.get('Cc', ''),
            'bcc': self.message.get('Bcc', ''),
            'date': self.message.get('Date', ''),
        }

    def get_body(self, part_type: str = 'text/plain') -> str:
        body = ""
        if self.message.is_multipart():
            for part in self.message.walk():
                content_type = part.get_content_type()
                if content_type == part_type:
                    try:
                        payload = part.get_payload(decode=True)
                        charset = part.get_content_charset() or 'utf-8'
                        body = payload.decode(charset, errors='replace')
                        break
                    except Exception as e:
                        print(f"Error decoding part: {e}")
        else:
            if self.message.get_content_type() == part_type:
                try:
                    payload = self.message.get_payload(decode=True)
                    charset = self.message.get_content_charset() or 'utf-8'
                    body = payload.decode(charset, errors='replace')
                except Exception as e:
                    print(f"Error decoding message: {e}")
        return body

    def get_plain_text(self) -> str:
        """Get plain text version of email."""
        return self.get_body('text/plain')

    def get_html(self) -> str:
        """Get HTML version of email."""
        return self.get_body('text/html')

    def get_attachments(self) -> List[Dict]:
        attachments = []
        if self.message.is_multipart():
            for part in self.message.walk():
                if part.get_content_disposition() == 'attachment':
                    attachments.append({
                        'filename': part.get_filename(),
                        'content_type': part.get_content_type(),
                        'size': len(part.get_payload(decode=True))
                    })
        return attachments

    def get_all_content(self) -> Dict:
        return {
            'headers': self.get_headers(),
            'plain_text': self.get_plain_text(),
            'html': self.get_html(),
            'attachments': self.get_attachments(),
        }

    def extract_sections(self) -> Dict[str, str]:
        sections = {
            'subject': self.get_headers()['subject'],
            'body': self.get_plain_text(),
        }
        body = sections['body']
        signature_markers = ['--', '\n\n--\n', 'Thanks', 'Best regards', 'Sincerely']
        for marker in signature_markers:
            if marker in body:
                parts = body.split(marker, 1)
                sections['body'] = parts[0].strip()
                sections['signature'] = marker + (parts[1] if len(parts) > 1 else '')
                break
        return sections
