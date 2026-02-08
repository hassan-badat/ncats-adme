import { Directive, Output, EventEmitter, HostListener, ElementRef, inject } from '@angular/core';

@Directive({
  selector: '[admeFileSelect]',
  standalone: true
})
export class FileSelectDirective {
  @Output() selectedFile = new EventEmitter<File | null>();
  
  private elementRef = inject(ElementRef);
  private fileInput: HTMLInputElement | null = null;
  
  @HostListener('click')
  onClick(): void {
    if (!this.fileInput) {
      this.fileInput = document.createElement('input');
      this.fileInput.type = 'file';
      this.fileInput.accept = '.csv,.txt,.smi,.smiles';
      this.fileInput.style.display = 'none';
      this.fileInput.addEventListener('change', (event) => this.onFileSelected(event));
      document.body.appendChild(this.fileInput);
    }
    this.fileInput.click();
  }
  
  private onFileSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0] || null;
    this.selectedFile.emit(file);
    // Reset input so same file can be selected again
    input.value = '';
  }
  
  ngOnDestroy(): void {
    if (this.fileInput) {
      this.fileInput.remove();
    }
  }
}

