/**
 * Root Page - Redirects to Dashboard
 */
import { redirect } from 'next/navigation';

export default function HomePage() {
  redirect('/dashboard');
}

