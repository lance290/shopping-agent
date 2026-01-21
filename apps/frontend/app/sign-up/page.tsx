import { SignUp } from '@clerk/nextjs';

export default function SignUpPage() {
  return (
    <main className="min-h-screen flex items-center justify-center bg-gray-50">
      <SignUp
        appearance={{
          elements: {
            rootBox: 'w-full max-w-md',
            card: 'shadow-md rounded-lg',
          },
        }}
        routing="hash"
        signInUrl="/login"
        forceRedirectUrl="/"
      />
    </main>
  );
}
