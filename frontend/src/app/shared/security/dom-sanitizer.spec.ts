import { SecurityContext } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { DomSanitizer } from '@angular/platform-browser';
import { DatePipe } from '@angular/common';

describe('Defensas de representación Angular', () => {
  it('elimina scripts y handlers, neutraliza javascript y conserva marcado benigno', () => {
    const sanitizer = TestBed.inject(DomSanitizer);
    const html = sanitizer.sanitize(SecurityContext.HTML,
      '<script>alert(1)</script><img src="x" onerror="alert(1)"><a href="javascript:alert(1)">x</a><b>texto</b>') ?? '';
    expect(html).not.toContain('<script');
    expect(html).not.toContain('onerror');
    expect(html).not.toContain('href="javascript:');
    expect(html).toContain('<b>texto</b>');
  });
  it('representa timestamps en UTC explícita independientemente de la zona del navegador', () => {
    expect(new DatePipe('en-US').transform('2026-11-18T01:30:00-05:00', 'yyyy-MM-dd HH:mm', 'UTC'))
      .toBe('2026-11-18 06:30');
  });
});
