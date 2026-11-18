import base64
import hashlib
import hmac
import json
import secrets
from datetime import timedelta
from time import time
from django.conf import settings
from django.core import signing
from django.db import transaction
from django.utils import timezone
from django_otp.oath import TOTP
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.tokens import RefreshToken
from core.models import MFALoginChallenge, Usuario
from core.services.crypto import encrypt, decrypt
from core.audit import audit


def challenge(user):
    nonce = secrets.token_urlsafe(32)
    token = signing.dumps({'uid': user.pk, 'nonce': nonce, 'epoch': user.mfa_epoch, 'pwd': hashlib.sha256(user.password.encode()).hexdigest()},
                          key=settings.MFA_KEY, salt='datapulse-mfa')
    MFALoginChallenge.objects.create(digest=hashlib.sha256(token.encode()).hexdigest(), usuario=user,
        expires=timezone.now() + timedelta(minutes=5))
    return {'mfa_required': True, 'mfa_token': token}


def verify_totp(user, code):
    if not user.mfa_secret_enc or not isinstance(code, str) or len(code) != 6 or not code.isascii() or not code.isdigit():
        return False
    raw = base64.b32decode(decrypt(user.mfa_secret_enc))
    totp = TOTP(raw, step=30, digits=6)
    totp.time = time()
    if not totp.verify(int(code), tolerance=1, min_t=user.mfa_last_t + 1):
        return False
    user.mfa_last_t = totp.t()
    user.save(update_fields=['mfa_last_t'])
    return True


def verify_factor(user, code):
    if verify_totp(user, code):
        return True
    if not user.recovery_codes_enc or not isinstance(code, str):
        return False
    hashes = json.loads(decrypt(user.recovery_codes_enc))
    candidate = hashlib.sha256(code.encode()).hexdigest()
    for index, stored in enumerate(hashes):
        if hmac.compare_digest(candidate, stored):
            hashes.pop(index)
            user.recovery_codes_enc = encrypt(json.dumps(hashes))
            user.save(update_fields=['recovery_codes_enc'])
            return True
    return False


def verify_login(token, code):
    try:
        payload = signing.loads(token, key=settings.MFA_KEY, salt='datapulse-mfa', max_age=300)
    except (signing.BadSignature, TypeError, ValueError) as exc:
        raise AuthenticationFailed() from exc
    failed = False
    with transaction.atomic():
        user = Usuario.objects.select_for_update().filter(pk=payload['uid'], rol='ADMIN', activo=True, is_active=True, mfa_enabled=True).first()
        record = MFALoginChallenge.objects.select_for_update().filter(digest=hashlib.sha256(token.encode()).hexdigest(),
            usuario=user, used=False, expires__gt=timezone.now()).first()
        if not user or not record or payload['epoch'] != user.mfa_epoch or not hmac.compare_digest(payload['pwd'], hashlib.sha256(user.password.encode()).hexdigest()):
            raise AuthenticationFailed()
        if not verify_factor(user, code):
            audit(user, 'MFA_VERIFY_FAIL', user)
            failed = True
        else:
            record.used = True
            record.save(update_fields=['used'])
            refresh = RefreshToken.for_user(user)
            refresh['mfa'] = True
            refresh['mfa_epoch'] = user.mfa_epoch
            audit(user, 'MFA_VERIFY_OK', user)
            result = {'access': str(refresh.access_token), 'refresh': str(refresh)}
    # Keep the failure audit committed; never return tokens on failure.
    if failed:
        raise AuthenticationFailed()
    return result
