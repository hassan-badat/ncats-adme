import { Directive, Input, ElementRef, inject, OnChanges, SimpleChanges } from '@angular/core';
import { ConfigService } from '@core/config.service';

@Directive({
  selector: '[admeStructureImage]',
  standalone: true
})
export class StructureImageDirective implements OnChanges {
  @Input() smiles = '';
  @Input() width = 200;
  @Input() height = 200;
  
  private elementRef = inject(ElementRef<HTMLImageElement>);
  private configService = inject(ConfigService);
  
  ngOnChanges(changes: SimpleChanges): void {
    if (changes['smiles'] || changes['width'] || changes['height']) {
      this.updateImage();
    }
  }
  
  private updateImage(): void {
    if (!this.smiles) {
      this.elementRef.nativeElement.src = '';
      return;
    }
    
    const encodedSmiles = encodeURIComponent(this.smiles);
    const baseUrl = this.configService.apiBaseUrl;
    this.elementRef.nativeElement.src = `${baseUrl}api/v1/structure?smiles=${encodedSmiles}&width=${this.width}&height=${this.height}`;
    this.elementRef.nativeElement.alt = this.smiles;
  }
}

