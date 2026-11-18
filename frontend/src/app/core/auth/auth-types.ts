export interface CaptchaAnswer {
  captcha_key: string;
  captcha_answer: string;
}
export interface CaptchaChallenge {
  captcha_key: string;
  image_url: string;
}
export interface MfaPending {
  mfa_required: true;
}
export type LogoutReason = 'expired' | 'revoked' | 'manual' | 'role_changed';
