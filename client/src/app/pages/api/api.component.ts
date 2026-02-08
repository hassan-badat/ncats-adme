import { Component, AfterViewInit, ViewEncapsulation } from '@angular/core';
import { CommonModule } from '@angular/common';

declare const SwaggerUIBundle: {
  (config: Record<string, unknown>): unknown;
  presets: { apis: unknown };
  SwaggerUIStandalonePreset: unknown;
  plugins: { DownloadUrl: unknown };
};

@Component({
  selector: 'adme-api',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './api.component.html',
  styleUrl: './api.component.scss',
  encapsulation: ViewEncapsulation.None
})
export class ApiComponent implements AfterViewInit {
  ngAfterViewInit(): void {
    if (typeof SwaggerUIBundle !== 'undefined') {
      SwaggerUIBundle({
        url: 'https://raw.githubusercontent.com/ncats/ncats-adme/development/client/src/assets/apidoc/swagger.yaml',
        dom_id: '#swagger-ui',
        layout: 'BaseLayout',
        docExpansion: 'list',
        defaultModelsExpandDepth: -1,
        presets: [
          SwaggerUIBundle.presets.apis,
          SwaggerUIBundle.SwaggerUIStandalonePreset
        ],
        plugins: [
          SwaggerUIBundle.plugins.DownloadUrl
        ]
      });
    }
  }
}

