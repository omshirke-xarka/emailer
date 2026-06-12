import re
import csv
import io
from urllib.parse import quote
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import pandas as pd
from ..models.contact import Contact, DynamicContact


def detect_delimiter(line: str) -> str:
    """Detect CSV delimiter from first line"""
    if '\t' in line:
        return '\t'
    return ','


def looks_like_header(fields: List[str]) -> bool:
    """Check if first row looks like headers"""
    known_headers = {
        'username', 'email', 'online', 'first name', 'last name', 'mobile',
        'subscribed', 'plan', 'pages left', 'created', 'last login',
        'draft used', 'research used', 'contract review', 'query',
        'judgment details', 'cart item'
    }
    
    # If most fields match known header names, it's a header row
    matches = sum(1 for f in fields if f.lower().strip() in known_headers)
    return matches >= 3


def canonical_header_mapping() -> Dict[str, str]:
    """Mapping from lowercase header to canonical header names"""
    return {
        'username': 'Username',
        'email': 'Email',
        'online': 'Online',
        'first name': 'First name',
        'first_name': 'First name',
        'firstname': 'First name',
        'last name': 'Last name',
        'last_name': 'Last name',
        'lastname': 'Last name',
        'mobile': 'Mobile',
        'subscribed': 'Subscribed',
        'plan': 'Plan',
        'pages left': 'Pages left',
        'pages_left': 'Pages left',
        'last login': 'Last login',
        'last_login': 'Last login',
        'draft used': 'Draft used',
        'draft_used': 'Draft used',
        'research used': 'Research used',
        'research_used': 'Research used',
        'contract review': 'Contract review',
        'contract_review': 'Contract review',
        'contact review': 'Contract review',
        'query': 'Query',
        'query_count': 'Query',
        'judgment details': 'Judgment details',
        'judgment_details': 'Judgment details',
        'cart item': 'Cart item',
        'cart_item': 'Cart item',
    }


def parse_csv_lines(content: str) -> Tuple[List[str], List[Dict[str, str]]]:
    """Parse CSV content and return headers and rows"""
    lines = content.strip().split('\n')
    if not lines:
        return [], []
    
    delimiter = detect_delimiter(lines[0])
    first_line_fields = [h.strip() for h in lines[0].split(delimiter)]
    
    # Determine if first line is header
    if looks_like_header(first_line_fields):
        raw_headers = first_line_fields
        data_start_index = 1
    else:
        raw_headers = [
            'Username', 'Email', 'Online', 'First name', 'Last name', 'Mobile',
            'Subscribed', 'Plan', 'Pages left', 'Created', 'Last login',
            'Draft used', 'Research used', 'Contract review', 'Query',
            'Judgment details', 'Cart item'
        ]
        data_start_index = 0
    
    # Map headers to canonical names
    canonical_headers = canonical_header_mapping()
    headers = [canonical_headers.get(h.lower(), h) for h in raw_headers]
    
    # Parse data rows
    rows = []
    for i in range(data_start_index, len(lines)):
        if not lines[i].strip():
            continue
            
        values = []
        current = ''
        in_quotes = False
        
        for ch in lines[i]:
            if ch == '"':
                in_quotes = not in_quotes
            elif ch == delimiter and not in_quotes:
                values.append(current.strip())
                current = ''
            elif ch in '\n\r':
                # Skip \n after \r
                if ch == '\r' and i + 1 < len(lines) and lines[i + 1] == '\n':
                    continue
                values.append(current.strip())
                current = ''
                break
            else:
                current += ch
        
        values.append(current.strip())
        
        # Create row dictionary
        row = {}
        for idx, header in enumerate(headers):
            row[header] = values[idx] if idx < len(values) else ''
        rows.append(row)
    
    return headers, rows


def row_to_contact(row: Dict[str, str], id: int) -> Optional[Contact]:
    """Convert CSV row to Contact object"""
    email = (row.get('Email', '') or '').strip()
    if not email:
        email = (row.get('Username', '') or '').strip()
    if not email:
        return None
    
    return Contact(
        id=id,
        username=row.get('Username', ''),
        email=email,
        online=row.get('Online', 'No'),
        first_name=row.get('First name') or None,
        last_name=row.get('Last name') or None,
        mobile=row.get('Mobile') or None,
        subscribed=row.get('Subscribed', 'No'),
        plan=row.get('Plan', 'Free Trial'),
        pages_left=int(row.get('Pages left', 0)),
        last_login=row.get('Last login') and row.get('Last login') != '—' and row.get('Last login') or None,
        draft_used=int(row.get('Draft used', 0)),
        research_used=int(row.get('Research used', 0)),
        contract_review=int(row.get('Contract review', 0)),
        query_count=int(row.get('Query', 0)),
        judgment_details=int(row.get('Judgment details', 0)),
        cart_item=row.get('Cart item') or None,
        created_at=datetime.now().isoformat(),
        updated_at=datetime.now().isoformat()
    )


def csv_to_contacts(csv_content: str) -> List[Contact]:
    """Convert CSV content to list of Contact objects"""
    _, rows = parse_csv_lines(csv_content)
    seen_emails = set()
    contacts = []
    id_counter = 1
    
    for row in rows:
        contact = row_to_contact(row, id_counter)
        if contact and contact.email.lower() not in seen_emails:
            seen_emails.add(contact.email.lower())
            contacts.append(contact)
            id_counter += 1
    
    return contacts


def parse_dynamic_csv(content: str) -> Tuple[List[str], List[Dict[str, str]]]:
    """Parse CSV content for dynamic contact lists"""
    delimiter = '\t' if '\t' in content else ','
    print(f"DEBUG: Detected delimiter: '{delimiter}'")
    
    # Use pandas for better CSV parsing
    try:
        df = pd.read_csv(io.StringIO(content), delimiter=delimiter)
        headers = df.columns.tolist()
        rows = df.to_dict('records')
        print(f"DEBUG: Pandas parsing successful - {len(headers)} headers, {len(rows)} rows")
        return headers, rows
    except Exception as e:
        print(f"DEBUG: Pandas parsing failed: {e}")
        # Fallback to manual parsing
        result = parse_csv_lines(content)
        print(f"DEBUG: Manual parsing fallback - {len(result[0])} headers, {len(result[1])} rows")
        return result


def csv_to_dynamic_contacts(csv_content: str) -> Tuple[List[str], List[DynamicContact]]:
    """Convert CSV content to dynamic contacts with columns"""
    print(f"DEBUG: Processing CSV content with {len(csv_content)} characters")
    headers, rows = parse_dynamic_csv(csv_content)
    print(f"DEBUG: Parsed headers: {headers}")
    print(f"DEBUG: Parsed {len(rows)} rows")
    if not headers:
        return [], []
    
    # Find email column for deduplication
    email_col = next((h for h in headers if 'email' in h.lower()), headers[0])
    
    seen_emails = set()
    contacts = []
    id_counter = 1
    
    for row in rows:
        email_val = str(row.get(email_col, '') or '').strip()
        if not email_val:
            continue
        
        email_key = email_val.lower()
        if email_key in seen_emails:
            continue
        
        seen_emails.add(email_key)
        
        # Create dynamic contact
        contact_data = {'id': id_counter}
        for header in headers:
            contact_data[header] = str(row.get(header, '') or '')
        
        contacts.append(DynamicContact(**contact_data))
        id_counter += 1
    
    return headers, contacts


def resolve_template(template: str, vars: Dict[str, str]) -> str:
    """Resolve template variables using {{variable}} syntax"""
    def replace_match(match):
        key = match.group(1).strip()
        return str(vars.get(key, match.group(0)))
    
    return re.sub(r'\{\{(\w[\w\s]*?)\}\}', replace_match, template)


def detect_email_column(columns: List[str]) -> str:
    """Detect email column from list of columns"""
    return next((col for col in columns if 'email' in col.lower()), columns[0])


def detect_name_column(columns: List[str]) -> Optional[str]:
    """Detect name column from list of columns"""
    for col in columns:
        if re.match(r'^(username|name|first.?name|full.?name)$', col.lower()):
            return col
    return None


def inject_preheader(html: str, preview_text: str) -> str:
    """Inject preheader text into HTML email"""
    preheader = f'<div style="display:none;max-height:0;overflow:hidden;mso-hide:all;">{preview_text}</div>'
    if '<body' in html:
        return re.sub(r'(<body[^>]*>)', rf'\1{preheader}', html, flags=re.IGNORECASE)
    return preheader + html


def inject_tracking_pixel(html: str, tracking_id: str) -> str:
    """Inject tracking pixel into HTML email"""
    from ..config import get_settings
    settings = get_settings()
    
    # Some clients skip display:none images, so keep the pixel rendered but invisible
    pixel = f'<img src="{settings.app_url}/api/track/open/{tracking_id}.png" width="1" height="1" border="0" alt="" style="width:1px;height:1px;border:0;margin:0;padding:0;" />'
    if '</body>' in html:
        return html.replace('</body>', f'{pixel}</body>')
    return html + pixel


def rewrite_links(html: str, tracking_id: str) -> str:
    """Rewrite links in HTML to include tracking"""
    from ..config import get_settings
    settings = get_settings()

    if not settings.enable_click_tracking:
        return html
    
    def replace_link(match):
        before = match.group(1)
        url = match.group(2)
        # Skip mailto:, tel:, and anchor links
        if re.match(r'^(mailto:|tel:|#)', url, re.IGNORECASE):
            return match.group(0)
        # Skip tracking URLs to avoid double-wrapping
        if '/api/track/' in url:
            return match.group(0)
        # Encode the entire destination as one query value so params with & = ? survive
        encoded_url = quote(url, safe="")
        redirect_url = f"{settings.app_url}/api/track/click/{tracking_id}?url={encoded_url}"
        return f'<a {before}href="{redirect_url}"'
    
    return re.sub(r'<a\s([^>]*?)href=["\']([^"\']+)["\']', replace_link, html, flags=re.IGNORECASE)
