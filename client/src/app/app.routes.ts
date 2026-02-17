import { Routes } from '@angular/router';

export const routes: Routes = [
  {
    path: '',
    loadComponent: () => import('./pages/home/home.component').then(m => m.HomeComponent),
    title: 'ADME@NCATS - Home'
  },
  {
    path: 'home',
    redirectTo: '',
    pathMatch: 'full'
  },
  {
    path: 'predictions',
    loadComponent: () => import('./pages/predictions/predictions.component').then(m => m.PredictionsComponent),
    title: 'ADME@NCATS - Predictions'
  },
  {
    path: 'models/:model',
    loadComponent: () => import('./pages/models/models.component').then(m => m.ModelsComponent),
    title: 'ADME@NCATS - Model Details'
  },
  {
    path: 'data',
    loadComponent: () => import('./pages/data/data.component').then(m => m.DataComponent),
    title: 'ADME@NCATS - Data'
  },
  {
    path: 'api',
    loadComponent: () => import('./pages/api/api.component').then(m => m.ApiComponent),
    title: 'ADME@NCATS - API'
  },
  {
    path: 'contact',
    loadComponent: () => import('./pages/contact/contact.component').then(m => m.ContactComponent),
    title: 'ADME@NCATS - Contact'
  },
  {
    path: '**',
    redirectTo: ''
  }
];

