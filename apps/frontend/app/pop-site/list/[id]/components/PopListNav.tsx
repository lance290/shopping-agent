import Link from 'next/link';
import Image from 'next/image';

interface PopListNavProps {
  id: string;
  isLoggedIn: boolean;
}

export default function PopListNav({ id, isLoggedIn }: PopListNavProps) {
  return (
    <nav className="sticky top-0 z-50 bg-white/80 backdrop-blur-md border-b border-gray-100">
      <div className="max-w-2xl mx-auto px-4 h-14 flex items-center justify-between">
        <Link href="/" className="flex items-center gap-2">
          <Image src="/pop-avatar.png" alt="Pop" width={32} height={32} className="rounded-full" />
          <span className="text-lg font-bold text-green-700">Pop</span>
        </Link>
        {isLoggedIn ? (
          <Link
            href={`/pop-site/chat?list=${id}`}
            className="text-sm bg-green-600 text-white px-4 py-2 rounded-full hover:bg-green-700 transition-colors"
          >
            + Add Items
          </Link>
        ) : (
          <Link
            href={`/login?brand=pop&redirect=/pop-site/list/${id}`}
            className="text-sm bg-green-600 text-white px-4 py-2 rounded-full hover:bg-green-700 transition-colors"
          >
            Sign In to Add
          </Link>
        )}
      </div>
    </nav>
  );
}
