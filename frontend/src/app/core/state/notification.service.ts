import { inject, Injectable } from '@angular/core';
import { MatSnackBar } from '@angular/material/snack-bar';
@Injectable({ providedIn: 'root' })
export class NotificationService {
  private readonly snack = inject(MatSnackBar);
  show(message: string): void {
    this.snack.open(message, 'Cerrar', {
      duration: 6500,
      horizontalPosition: 'end',
      verticalPosition: 'bottom',
    });
  }
}
