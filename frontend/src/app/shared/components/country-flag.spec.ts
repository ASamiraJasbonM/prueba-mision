import { TestBed } from '@angular/core/testing';
import { CountryFlag } from './country-flag';

describe('CountryFlag', () => {
  it('uses a local asset and recovers gracefully when the image fails', () => {
    const fixture = TestBed.createComponent(CountryFlag);
    fixture.componentRef.setInput('code', 'co');
    fixture.componentRef.setInput('name', 'Colombia');
    fixture.detectChanges();
    const image = fixture.nativeElement.querySelector('img') as HTMLImageElement;
    expect(image.getAttribute('src')).toBe('/assets/flags/co.svg');
    expect(image.alt).toBe('Bandera de Colombia');
    image.dispatchEvent(new Event('error'));
    fixture.detectChanges();
    expect(fixture.nativeElement.querySelector('img')).toBeNull();
    expect(fixture.nativeElement.textContent).toContain('Bandera no disponible');
    fixture.destroy();
  });

  it('rejects unknown codes and URL/path input rather than loading remote images', () => {
    const fixture = TestBed.createComponent(CountryFlag);
    for (const code of ['ZZ', '../co', 'https://example.com/flag.svg']) {
      fixture.componentRef.setInput('code', code);
      fixture.detectChanges();
      expect(fixture.nativeElement.querySelector('img')).toBeNull();
    }
    fixture.destroy();
  });
});
