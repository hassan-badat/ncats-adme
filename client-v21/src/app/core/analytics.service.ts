import { Injectable, inject, PLATFORM_ID } from '@angular/core';
import { isPlatformBrowser } from '@angular/common';
import { ConfigService } from './config.service';

declare global {
  interface Window {
    gtag: (...args: unknown[]) => void;
    dataLayer: unknown[];
  }
}

interface GAPageView {
  page_title?: string;
  page_path?: string;
}

interface GAEvent {
  event_category?: string;
  event_label?: string;
  value?: number;
}

interface GAException {
  description: string;
  fatal: boolean;
}

@Injectable({
  providedIn: 'root'
})
export class AnalyticsService {
  private configService = inject(ConfigService);
  private platformId = inject(PLATFORM_ID);
  
  private googleAnalyticsId: string | null = null;
  private isActive = false;
  private gtag: ((...args: unknown[]) => void) | null = null;

  constructor() {
    if (isPlatformBrowser(this.platformId)) {
      this.init();
    }
  }

  private init(): void {
    const gaId = this.configService.configData?.googleAnalyticsId;
    if (gaId && typeof window !== 'undefined' && window.gtag) {
      this.googleAnalyticsId = gaId;
      this.gtag = window.gtag;
      this.gtag('config', this.googleAnalyticsId, { send_page_view: false });
      this.isActive = true;
    }
  }

  sendPageView(title?: string, path: string = location.href): void {
    if (!this.isActive || !this.gtag || !this.googleAnalyticsId) return;

    const sendFields: GAPageView = {
      page_title: title,
      page_path: path
    };
    this.gtag('config', this.googleAnalyticsId, sendFields);
  }

  sendEvent(eventAction: string, eventCategory?: string, eventLabel?: string, eventValue?: number): void {
    if (!this.isActive || !this.gtag) return;

    const sendFields: GAEvent = {
      event_category: eventCategory,
      event_label: eventLabel,
      value: eventValue
    };
    this.gtag('event', eventAction, sendFields);
  }

  sendException(description: string, fatal = false): void {
    if (!this.isActive || !this.gtag) return;

    const sendFields: GAException = {
      description,
      fatal
    };
    this.gtag('event', 'exception', sendFields);
  }
}

