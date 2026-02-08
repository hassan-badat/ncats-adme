import { Component, Input, Output, EventEmitter, ViewChild, ElementRef, OnInit, AfterViewInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { DomSanitizer, SafeResourceUrl } from '@angular/platform-browser';

declare global {
  interface Window {
    ketcher?: {
      getSmiles(): string;
      setMolecule(mol: string): void;
      editor?: {
        on(event: string, handler: () => void): void;
      };
    };
  }
}

@Component({
  selector: 'adme-sketcher',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './sketcher.component.html',
  styleUrl: './sketcher.component.scss'
})
export class SketcherComponent implements OnInit, AfterViewInit {
  @ViewChild('ketcherFrame') ketcherFrame!: ElementRef<HTMLIFrameElement>;
  @Input() apiBaseUrl = '';
  @Output() moleculeInput = new EventEmitter<string>();
  
  private sanitizer = inject(DomSanitizer);
  private ketcher: Window['ketcher'] | null = null;
  
  hasValidMolecule = false;
  ketcherSrc!: SafeResourceUrl;
  
  ngOnInit(): void {
    const baseUrl = this.apiBaseUrl || '';
    this.ketcherSrc = this.sanitizer.bypassSecurityTrustResourceUrl(
      `assets/ketcher/ketcher.html?api_path=${baseUrl}`
    );
  }
  
  ngAfterViewInit(): void {
    this.ketcherFrame.nativeElement.onload = () => {
      const frameWindow = this.ketcherFrame.nativeElement.contentWindow;
      if (frameWindow) {
        this.ketcher = (frameWindow as Window & { ketcher?: Window['ketcher'] }).ketcher;
        
        if (this.ketcher?.editor) {
          this.ketcher.editor.on('change', () => {
            this.checkMolecule();
          });
        }
      }
    };
  }
  
  private checkMolecule(): void {
    if (this.ketcher) {
      const smiles = this.ketcher.getSmiles();
      this.hasValidMolecule = !!smiles && smiles.trim().length > 0;
    }
  }
  
  submitMolecule(): void {
    if (this.ketcher) {
      const smiles = this.ketcher.getSmiles();
      if (smiles) {
        this.moleculeInput.emit(smiles);
      }
    }
  }
}
