import { Component, Input, signal } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'adme-models',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './models.component.html',
  styleUrl: './models.component.scss'
})
export class ModelsComponent {
  modelType = signal('rlm');
  
  @Input() set model(value: string) {
    this.modelType.set(value || 'rlm');
  }
}

