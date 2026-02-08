import { Component, Input, Output, EventEmitter, signal } from '@angular/core';
import { CommonModule } from '@angular/common';

export interface Tab {
  label: string;
  id?: string;
  disabled?: boolean;
}

@Component({
  selector: 'adme-tab-group',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './tab-group.component.html',
  styleUrl: './tab-group.component.scss'
})
export class TabGroupComponent {
  @Input() tabs: Tab[] = [];
  @Input() set selectedTabIndex(value: number) {
    this._selectedIndex.set(value);
  }
  @Output() tabChange = new EventEmitter<{ index: number; tab: Tab }>();
  
  private _selectedIndex = signal(0);
  
  get selectedIndex(): number {
    return this._selectedIndex();
  }
  
  selectTab(index: number, tab: Tab): void {
    if (tab.disabled) return;
    this._selectedIndex.set(index);
    this.tabChange.emit({ index, tab });
  }
}
