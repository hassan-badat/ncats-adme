import { Component, Input, Output, EventEmitter, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { PaginatorComponent, PageEvent } from '../paginator/paginator.component';

export interface TableColumn {
  key: string;
  label: string;
  sortable?: boolean;
  type?: 'text' | 'image' | 'link';
  description?: string;
}

export interface SortEvent {
  column: string;
  direction: 'asc' | 'desc' | '';
}

@Component({
  selector: 'adme-data-table',
  standalone: true,
  imports: [CommonModule, PaginatorComponent],
  template: `
    <div class="data-table-wrapper">
      <div class="table-container">
        <table class="data-table">
          <thead>
            <tr>
              @for (column of columns; track column.key) {
                <th 
                  [class.sortable]="column.sortable"
                  [class.sorted]="sortColumn() === column.key"
                  (click)="column.sortable && onSort(column.key)"
                  [title]="column.description || column.label"
                >
                  <span class="header-content">
                    {{ column.label }}
                    @if (column.sortable) {
                      <span class="sort-icon">
                        @if (sortColumn() === column.key) {
                          @if (sortDirection() === 'asc') {
                            <svg viewBox="0 0 24 24" fill="currentColor">
                              <path d="M7 14l5-5 5 5z"/>
                            </svg>
                          } @else {
                            <svg viewBox="0 0 24 24" fill="currentColor">
                              <path d="M7 10l5 5 5-5z"/>
                            </svg>
                          }
                        } @else {
                          <svg viewBox="0 0 24 24" fill="currentColor" class="sort-inactive">
                            <path d="M12 5.83L15.17 9l1.41-1.41L12 3 7.41 7.59 8.83 9 12 5.83zm0 12.34L8.83 15l-1.41 1.41L12 21l4.59-4.59L15.17 15 12 18.17z"/>
                          </svg>
                        }
                      </span>
                    }
                  </span>
                </th>
              }
            </tr>
          </thead>
          <tbody>
            @for (row of pagedData(); track $index) {
              <tr (click)="rowClick.emit(row)">
                @for (column of columns; track column.key) {
                  <td>
                    @if (column.type === 'image') {
                      <button class="image-btn" (click)="imageClick.emit({row, column}); $event.stopPropagation()">
                        <img [src]="getImageUrl(row[column.key])" [alt]="row[column.key]" class="cell-image" loading="lazy" />
                      </button>
                    } @else if (column.type === 'link') {
                      <a [href]="row[column.key]" target="_blank" rel="noopener">{{ row[column.key] }}</a>
                    } @else {
                      {{ formatCellValue(row[column.key]) }}
                    }
                  </td>
                }
              </tr>
            } @empty {
              <tr class="empty-row">
                <td [attr.colspan]="columns.length">
                  <div class="empty-state">
                    <svg viewBox="0 0 24 24" fill="currentColor">
                      <path d="M19 5v14H5V5h14m0-2H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2z"/>
                    </svg>
                    <p>No data available</p>
                  </div>
                </td>
              </tr>
            }
          </tbody>
        </table>
      </div>
      
      @if (showPagination && data.length > 0) {
        <adme-paginator
          [length]="data.length"
          [pageIndex]="pageIndex()"
          [pageSize]="pageSize()"
          [pageSizeOptions]="pageSizeOptions"
          (page)="onPageChange($event)"
        />
      }
    </div>
  `,
  styles: [`
    .data-table-wrapper {
      background: var(--surface);
      border-radius: var(--radius-md);
      box-shadow: var(--shadow-sm);
      overflow: hidden;
    }
    
    .table-container {
      overflow-x: auto;
    }
    
    .data-table {
      width: 100%;
      border-collapse: collapse;
      
      th, td {
        padding: var(--spacing-md);
        text-align: left;
        border-bottom: 1px solid var(--border-color-light);
        vertical-align: middle;
      }
      
      th {
        background: var(--primary-lightest);
        font-weight: var(--font-weight-semibold);
        color: var(--text-primary);
        white-space: nowrap;
        user-select: none;
        
        &.sortable {
          cursor: pointer;
          
          &:hover {
            background: var(--primary-lighter);
          }
        }
        
        &.sorted {
          background: var(--primary-lighter);
          color: var(--primary-dark);
        }
      }
      
      .header-content {
        display: flex;
        align-items: center;
        gap: var(--spacing-xs);
      }
      
      .sort-icon {
        display: flex;
        
        svg {
          width: 18px;
          height: 18px;
        }
        
        .sort-inactive {
          opacity: 0.3;
        }
      }
      
      td {
        color: var(--text-secondary);
        font-size: 0.9375rem;
      }
      
      tbody tr {
        transition: background var(--transition-fast);
        
        &:hover {
          background: var(--gray-50);
        }
        
        &:last-child td {
          border-bottom: none;
        }
      }
    }
    
    .image-btn {
      padding: 0;
      background: transparent;
      border: 2px solid var(--border-color);
      border-radius: var(--radius-sm);
      cursor: pointer;
      transition: all var(--transition-fast);
      overflow: hidden;
      
      &:hover {
        border-color: var(--primary);
        box-shadow: var(--shadow-sm);
      }
    }
    
    .cell-image {
      display: block;
      width: 60px;
      height: 60px;
      object-fit: contain;
      background: white;
    }
    
    .empty-row td {
      padding: var(--spacing-xxl);
    }
    
    .empty-state {
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: var(--spacing-md);
      color: var(--text-hint);
      
      svg {
        width: 48px;
        height: 48px;
        opacity: 0.5;
      }
      
      p {
        margin: 0;
        font-size: 0.9375rem;
      }
    }
  `]
})
export class DataTableComponent {
  @Input() columns: TableColumn[] = [];
  @Input() data: Record<string, unknown>[] = [];
  @Input() showPagination = true;
  @Input() pageSizeOptions = [5, 10, 25, 100];
  @Input() defaultPageSize = 10;
  @Input() imageUrlFn?: (value: unknown) => string;
  
  @Output() rowClick = new EventEmitter<Record<string, unknown>>();
  @Output() imageClick = new EventEmitter<{ row: Record<string, unknown>; column: TableColumn }>();
  @Output() sortChange = new EventEmitter<SortEvent>();
  
  private _pageIndex = signal(0);
  private _pageSize = signal(10);
  private _sortColumn = signal<string>('');
  private _sortDirection = signal<'asc' | 'desc' | ''>('');
  
  pageIndex = computed(() => this._pageIndex());
  pageSize = computed(() => this._pageSize());
  sortColumn = computed(() => this._sortColumn());
  sortDirection = computed(() => this._sortDirection());
  
  pagedData = computed(() => {
    const start = this._pageIndex() * this._pageSize();
    const end = start + this._pageSize();
    return this.sortedData().slice(start, end);
  });
  
  sortedData = computed(() => {
    const column = this._sortColumn();
    const direction = this._sortDirection();
    
    if (!column || !direction) {
      return [...this.data];
    }
    
    return [...this.data].sort((a, b) => {
      const aVal = a[column];
      const bVal = b[column];
      
      if (aVal === bVal) return 0;
      if (aVal === null || aVal === undefined) return 1;
      if (bVal === null || bVal === undefined) return -1;
      
      const comparison = aVal < bVal ? -1 : 1;
      return direction === 'asc' ? comparison : -comparison;
    });
  });
  
  ngOnInit(): void {
    this._pageSize.set(this.defaultPageSize);
  }
  
  onSort(column: string): void {
    if (this._sortColumn() === column) {
      // Toggle direction
      const newDir = this._sortDirection() === 'asc' ? 'desc' : this._sortDirection() === 'desc' ? '' : 'asc';
      this._sortDirection.set(newDir);
      if (!newDir) this._sortColumn.set('');
    } else {
      this._sortColumn.set(column);
      this._sortDirection.set('asc');
    }
    
    this.sortChange.emit({
      column: this._sortColumn(),
      direction: this._sortDirection()
    });
  }
  
  onPageChange(event: PageEvent): void {
    this._pageIndex.set(event.pageIndex);
    this._pageSize.set(event.pageSize);
  }
  
  getImageUrl(value: unknown): string {
    if (this.imageUrlFn) {
      return this.imageUrlFn(value);
    }
    return String(value);
  }
  
  formatCellValue(value: unknown): string {
    if (value === null || value === undefined) return '';
    if (value === '0 (0.0)') return '0 (0.01)';
    return String(value);
  }
}

