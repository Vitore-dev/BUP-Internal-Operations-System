"""What the new employee must fill in, and the checks on it. Nothing here saves anything."""

import datetime as dt
import re

MAX_FILE_BYTES = 5 * 1024 * 1024
MAX_FILES = 12
# the first bytes of a genuine file of each type, so a renamed program or script cannot pass as a scan
SIGNATURES = {'.pdf': (b'%PDF',), '.jpg': (b'\xff\xd8\xff',), '.jpeg': (b'\xff\xd8\xff',), '.png': (b'\x89PNG\r\n\x1a\n',)}
DOC_KINDS = ['ID_COPY', 'HEALTH_CERT', 'EXEMPTION_CERT', 'QUALIFICATIONS']

PHONE_RE = re.compile(r'^[0-9+()\-\s]{7,20}$')
ID_RE = re.compile(r'^[A-Za-z0-9\-/ ]{4,30}$')
ACCOUNT_RE = re.compile(r'^[0-9 ]{4,24}$')
BRANCH_RE = re.compile(r'^[0-9A-Za-z\- ]{2,12}$')
EMAIL_RE = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')

GENDERS = ('FEMALE', 'MALE', 'PREFER_NOT')
MARITAL = ('SINGLE', 'MARRIED', 'DIVORCED', 'WIDOWED', 'OTHER')

# (field, label, how it is checked). Required unless marked optional.
TEXT_FIELDS = [
    ('full_names', 'Names', 200), ('postal_address', 'Postal address', 500), ('physical_address', 'Physical address', 500),
    ('position_title', 'Position title', 200), ('program', 'Program', 200),
    ('kin_name', 'Next of kin names', 200), ('kin_relationship', 'Next of kin relationship', 100),
    ('emergency_name', 'Emergency contact names', 200), ('emergency_relationship', 'Emergency contact relationship', 100),
    ('bank_name', 'Bank name', 100), ('bank_branch_name', 'Branch name', 100), ('bank_account_name', 'Names appearing on the account', 200),
]
PHONE_FIELDS = [('telephone', 'Telephone no.'), ('kin_telephone', 'Next of kin telephone'), ('emergency_telephone', 'Emergency contact telephone')]


def _date(value):
    try:
        return dt.date.fromisoformat((value or '').strip())
    except ValueError:
        return None


def validate_submission(post, today=None):
    """Returns (clean values, {field: error message}). clean always holds what was typed, so a form can be shown again without losing it."""
    today = today or dt.date.today()
    get = lambda k: (post.get(k) or '').strip()
    clean, errors = {}, {}

    for field, label, limit in TEXT_FIELDS:
        clean[field] = get(field)
        if not clean[field]:
            errors[field] = f'Please fill in: {label}.'
        elif len(clean[field]) > limit:
            errors[field] = f'{label} is too long.'
    clean['qualifications'] = get('qualifications')
    if len(clean['qualifications']) > 2000:
        errors['qualifications'] = 'Academic qualifications is too long (2000 characters at most).'

    for field, label in PHONE_FIELDS:
        clean[field] = get(field)
        if not PHONE_RE.match(clean[field]):
            errors[field] = f'Please give a telephone number for: {label}. Use digits, spaces, + and - only.'

    clean['email_address'] = get('email_address').lower()
    if not EMAIL_RE.match(clean['email_address']):
        errors['email_address'] = 'Please give a valid e-mail address.'

    clean['gender'] = get('gender')
    if clean['gender'] not in GENDERS:
        errors['gender'] = 'Please choose a gender (or "Prefer not to say").'
    clean['marital_status'] = get('marital_status')
    if clean['marital_status'] not in MARITAL:
        errors['marital_status'] = 'Please choose your marital status.'

    clean['id_number'] = get('id_number')
    if not ID_RE.match(clean['id_number']):
        errors['id_number'] = 'Please give your ID (Omang) or passport number.'

    raw_birth = get('date_of_birth'); clean['date_of_birth'] = _date(raw_birth)
    if clean['date_of_birth'] is None:
        errors['date_of_birth'] = 'Please give your date of birth.'
    elif not (dt.date(1930, 1, 1) <= clean['date_of_birth'] <= dt.date(today.year - 16, today.month, min(today.day, 28))):
        errors['date_of_birth'] = 'That date of birth does not look right.'

    raw_exp = get('id_expiry'); clean['id_expiry'] = _date(raw_exp)
    if raw_exp and clean['id_expiry'] is None:
        errors['id_expiry'] = 'The expiry date is not a valid date.'
    elif clean['id_expiry'] and clean['id_expiry'] < today:
        errors['id_expiry'] = 'That document has expired. Please give the expiry date of a current one.'

    raw_start = get('assumption_date'); clean['assumption_date'] = _date(raw_start)
    if clean['assumption_date'] is None:
        errors['assumption_date'] = 'Please give your date of assumption of duty.'
    elif not (today - dt.timedelta(days=3 * 365) <= clean['assumption_date'] <= today + dt.timedelta(days=3 * 365)):
        errors['assumption_date'] = 'That start date does not look right.'

    clean['bank_branch_code'] = get('bank_branch_code')
    if not BRANCH_RE.match(clean['bank_branch_code']):
        errors['bank_branch_code'] = 'Please give the branch code.'
    clean['bank_account_number'] = get('bank_account_number')
    if not ACCOUNT_RE.match(clean['bank_account_number']):
        errors['bank_account_number'] = 'Please give the account number (digits only).'

    clean['declaration_name'] = get('declaration_name')
    if len(clean['declaration_name']) < 2:
        errors['declaration_name'] = 'Please type your full name to sign.'
    if get('declaration') != 'yes':
        errors['declaration'] = 'Please tick the box to confirm your details are correct.'
    return clean, errors


def validate_upload(uploaded):
    """One attached file: an allowed type, really that type, and not too big. Returns an error message or None."""
    name = getattr(uploaded, 'name', '') or ''
    ext = ('.' + name.rsplit('.', 1)[-1].lower()) if '.' in name else ''
    if ext not in SIGNATURES:
        return f'"{name}" is not allowed. Please attach a PDF, JPG or PNG.'
    if uploaded.size > MAX_FILE_BYTES:
        return f'"{name}" is larger than {MAX_FILE_BYTES // (1024 * 1024)} MB. Please send a smaller scan.'
    if uploaded.size == 0:
        return f'"{name}" is empty.'
    head = uploaded.read(8)
    uploaded.seek(0)
    if not any(head.startswith(sig) for sig in SIGNATURES[ext]):
        return f'"{name}" does not look like a real {ext[1:].upper()} file.'
    return None


def validate_uploads(files_by_kind):
    """files_by_kind: {kind: [uploaded files]}. Returns a list of error messages (empty when fine)."""
    errors = []
    total = sum(len(v) for v in files_by_kind.values())
    if not files_by_kind.get('ID_COPY'):
        errors.append('Please attach a copy of your passport or Omang.')
    if total > MAX_FILES:
        errors.append(f'Please attach no more than {MAX_FILES} files in all.')
    for kind, files in files_by_kind.items():
        for f in files:
            problem = validate_upload(f)
            if problem:
                errors.append(problem)
    return errors
