'use client';

import { use } from 'react';
import Link from 'next/link';
import Image from 'next/image';

export default function PopInvitePage({ params }: { params: Promise<{ code: string }> }) {
  const { code } = use(params);

  return (
    <div className="min-h-screen bg-gradient-to-b from-green-50 to-white flex flex-col items-center justify-center px-4">
      <div className="max-w-md w-full text-center">
        <Image src="/pop-avatar.png" alt="Pop" width={80} height={80} className="rounded-full mx-auto mb-6 shadow-lg border-4 border-white" />
        <h1 className="text-3xl font-bold text-gray-900 mb-3">
          You&apos;re invited to a family list!
        </h1>
        <p className="text-gray-600 mb-8">
          Someone wants to share their grocery list with you on Pop.
          Join to build your list together and save money as a family.
        </p>

        <div className="space-y-3">
          <Link
            href={`/login?invite=${code}&brand=pop`}
            className="block w-full bg-green-600 text-white font-semibold py-4 rounded-2xl hover:bg-green-700 transition-colors text-lg"
          >
            Join the List
          </Link>
          <Link
            href="/"
            className="block w-full text-gray-500 font-medium py-3 rounded-2xl hover:bg-gray-100 transition-colors"
          >
            Learn more about Pop
          </Link>
        </div>

        <div className="mt-12 bg-white rounded-2xl p-6 shadow-sm text-left">
          <h3 className="text-sm font-semibold text-gray-900 mb-3">What is Pop?</h3>
          <ul className="space-y-3 text-sm text-gray-600">
            <li className="flex items-start gap-2">
              <span className="text-green-500 mt-0.5">✓</span>
              <span>Shared family grocery list — everyone adds items</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-green-500 mt-0.5">✓</span>
              <span>AI finds deals and coupons for every item</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-green-500 mt-0.5">✓</span>
              <span>Snap your receipt to earn money back</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-green-500 mt-0.5">✓</span>
              <span>Works via text, email, or web — your choice</span>
            </li>
          </ul>
        </div>

        <p className="mt-8 text-xs text-gray-400">
          Invite code: {code}
        </p>
      </div>
    </div>
  );
}
