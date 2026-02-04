import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { environment } from '@env/environment';

export interface Config {
  apiBaseUrl: string;
  googleAnalyticsId?: string;
  releaseDate?: string;
  releaseUrl?: string;
  tagName?: string;
}

@Injectable({
  providedIn: 'root'
})
export class ConfigService {
  private http = inject(HttpClient);
  private _configData: Config | null = null;

  get configData(): Config {
    return this._configData || {
      apiBaseUrl: environment.apiBaseUrl
    };
  }

  get apiBaseUrl(): string {
    return this._configData?.apiBaseUrl || environment.apiBaseUrl;
  }

  load(): Promise<void> {
    return this.http
      .get<Config>('assets/data/config.json')
      .toPromise()
      .then((config) => {
        if (config) {
          this._configData = {
            ...config,
            apiBaseUrl: config.apiBaseUrl || environment.apiBaseUrl,
            googleAnalyticsId: config.googleAnalyticsId || environment.googleAnalyticsId
          };
        }
      })
      .catch(() => {
        // Use environment defaults if config file not found
        this._configData = {
          apiBaseUrl: environment.apiBaseUrl,
          googleAnalyticsId: environment.googleAnalyticsId
        };
      });
  }
}

