import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';

interface TeamMember {
  name: string;
  title: string;
  email?: string;
  image: string;
  isCurrent: boolean;
  company?: string;
}

@Component({
  selector: 'adme-contact',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './contact.component.html',
  styleUrl: './contact.component.scss'
})
export class ContactComponent {
  currentMembers: TeamMember[] = [
    { name: 'Pranav Shah', title: 'Lead, In Vitro ADME (DMPK Group)', email: 'pranav.shah@nih.gov', image: 'assets/profile_images/pranav.jpeg', isCurrent: true },
    { name: 'Ewy A. Mathé', title: 'Director (Informatics Core)', email: 'ewy.mathe@nih.gov', image: 'assets/profile_images/ewy.png', isCurrent: true },
    { name: 'Xin Xu', title: 'Lead (DMPK Group)', email: 'xin.xu3@nih.gov', image: 'assets/profile_images/xin.jpg', isCurrent: true },
    { name: 'Claire Weber', title: 'Postbaccalaureate Fellow (DMPK Group)', email: 'claire.weber2@nih.gov', image: 'assets/profile_images/claire.jpg', isCurrent: true },
    { name: 'Gyutae Lim', title: 'Postdoctoral Fellow (DMPK Group)', email: 'gyutae.lim@nih.gov', image: 'assets/profile_images/gyutae.jpg', isCurrent: true },
    { name: 'Nivedita Kinatukara', title: 'Postbaccalaureate Fellow (DMPK Group)', email: 'nivedita.kinatukara@nih.gov', image: 'assets/profile_images/nivedita.jpg', isCurrent: true }
  ];
  
  formerMembers: TeamMember[] = [
    { name: 'Vishal B. Siramshetty', title: 'Genentech', image: 'assets/profile_images/vishal.jpg', isCurrent: false, company: 'Genentech' },
    { name: 'Dac-Trung Nguyen', title: 'Pfizer', image: 'assets/profile_images/trung.jpg', isCurrent: false, company: 'Pfizer' },
    { name: 'Noel T. Southall', title: 'AstraZeneca', image: 'assets/profile_images/noel.jpg', isCurrent: false, company: 'AstraZeneca' },
    { name: 'Jorge Neyra', title: 'Somatus', image: 'assets/profile_images/jorge.jpg', isCurrent: false, company: 'Somatus' },
    { name: 'Jordan Williams', title: 'University of Pennsylvania', image: 'assets/profile_images/jordan.jpg', isCurrent: false, company: 'University of Pennsylvania' },
    { name: 'Rintaro Kato', title: 'Former Postbaccalaureate Fellow (DMPK Group)', image: 'assets/profile_images/rintaro.jpg', isCurrent: false }
  ];
  
  resources = [
    { name: 'RDKit', url: 'https://www.rdkit.org/', image: 'assets/images/rdkit.png' },
    { name: 'Python', url: 'https://www.python.org/', image: 'assets/images/python.png' },
    { name: 'Angular', url: 'https://angular.io/', image: 'assets/images/angular.png' },
    { name: 'EPAM Ketcher', url: 'https://lifescience.opensource.epam.com/ketcher/index.html', image: 'assets/images/epam_ketcher.png' }
  ];
}

