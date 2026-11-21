export interface NavItem {
  href: '/' | '/entries' | '/recurring' | '/vat' | '/counterparties' | '/settings';
  label: string;
}

export const navItems: NavItem[] = [
  { href: '/', label: 'Dashboard' },
  { href: '/entries', label: 'Entries' },
  { href: '/recurring', label: 'Recurring' },
  { href: '/vat', label: 'VAT' },
  { href: '/counterparties', label: 'Counterparties' },
  { href: '/settings', label: 'Settings' }
];

export function isActive(pathname: string, href: NavItem['href']): boolean {
  return href === '/' ? pathname === '/' : pathname === href || pathname.startsWith(`${href}/`);
}
