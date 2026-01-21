import { SignIn } from '@clerk/nextjs';

export default function LoginPage() {
  return (
    <main className="min-h-screen flex items-center justify-center bg-gray-50">
      <SignIn
        appearance={{
          elements: {
            rootBox: 'w-full max-w-md',
            card: 'shadow-md rounded-lg',
          },
        }}
        routing="hash"
        signUpUrl="/sign-up"
        forceRedirectUrl="/"
      />
    </main>
  );
}
