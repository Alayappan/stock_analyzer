import { Injectable, signal } from '@angular/core';

export interface ToastMessage {
  id: string;
  type: 'success' | 'error' | 'info' | 'warning';
  title?: string;
  message: string;
}

@Injectable({
  providedIn: 'root'
})
export class ToastService {
  toasts = signal<ToastMessage[]>([]);

  show(type: 'success' | 'error' | 'info' | 'warning', message: string, title?: string) {
    const id = Math.random().toString(36).substring(2, 9);
    const newToast: ToastMessage = { id, type, message, title };
    this.toasts.update(list => [...list, newToast]);

    setTimeout(() => {
      this.dismiss(id);
    }, 4500);
  }

  success(message: string, title: string = 'Success') {
    this.show('success', message, title);
  }

  error(message: string, title: string = 'Error') {
    this.show('error', message, title);
  }

  info(message: string, title: string = 'Information') {
    this.show('info', message, title);
  }

  warning(message: string, title: string = 'Notice') {
    this.show('warning', message, title);
  }

  dismiss(id: string) {
    this.toasts.update(list => list.filter(t => t.id !== id));
  }
}
