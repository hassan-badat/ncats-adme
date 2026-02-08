import { Component, Input, Output, EventEmitter, HostListener } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'adme-modal-dialog',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './modal-dialog.component.html',
  styleUrl: './modal-dialog.component.scss'
})
export class ModalDialogComponent {
  @Input() open = false;
  @Input() title = '';
  @Input() showFooter = true;
  @Input() confirmLabel = 'Confirm';
  @Input() cancelLabel = 'Cancel';
  
  @Output() closed = new EventEmitter<void>();
  @Output() confirmed = new EventEmitter<void>();
  
  @HostListener('document:keydown.escape')
  onEscapeKey(): void {
    if (this.open) {
      this.close();
    }
  }
  
  close(): void {
    this.closed.emit();
  }
  
  confirm(): void {
    this.confirmed.emit();
    this.close();
  }
  
  onBackdropClick(event: MouseEvent): void {
    if ((event.target as HTMLElement).classList.contains('modal-backdrop')) {
      this.close();
    }
  }
}
