import Link from 'next/link';

const GUIDES = [
  {
    title: 'Private aviation: charter vs. fractional vs. jet card',
    desc: 'A practical breakdown of cost structures, availability trade-offs, and when each model makes sense for high-frequency travelers.',
    tag: 'Service',
    slug: 'private-aviation',
  },
  {
    title: 'Sourcing bespoke menswear in 2025',
    desc: 'From Savile Row to Neapolitan houses — lead times, fitting travel requirements, and how to manage the process remotely.',
    tag: 'Luxury',
    slug: 'bespoke-menswear',
  },
  {
    title: 'Art acquisition for new collectors',
    desc: 'Primary vs. secondary market, gallery relationships, authentication basics, and what to ask before committing to a six-figure piece.',
    tag: 'Luxury',
    slug: 'art-acquisition',
  },
  {
    title: 'Home automation for estate properties',
    desc: 'Evaluating Crestron, Control4, and Savant across multi-structure properties — integrators, ongoing support costs, and resale impact.',
    tag: 'Service',
    slug: 'estate-automation',
  },
  {
    title: 'Executive relocation: vendor vetting checklist',
    desc: 'How to evaluate moving firms, secure storage, and manage white-glove household goods transport across international moves.',
    tag: 'EA Guide',
    slug: 'executive-relocation',
  },
  {
    title: 'Luxury vehicle acquisition: new vs. pre-owned exotics',
    desc: 'Dealer relationships, CPO programs, independent inspection protocols, and where auctions fit into a serious buying strategy.',
    tag: 'Luxury',
    slug: 'luxury-vehicles',
  },
];

const TAG_STYLES: Record<string, string> = {
  Trending: 'bg-red-500/15 text-red-400',
  Popular: 'bg-gold/15 text-gold-dark',
  Seasonal: 'bg-amber-500/15 text-amber-400',
  Rising: 'bg-emerald-500/15 text-emerald-400',
  Luxury: 'bg-purple-500/15 text-purple-300',
  Service: 'bg-sky-500/15 text-sky-300',
  'EA Guide': 'bg-amber-500/15 text-amber-300',
};

export default function GuidesIndexPage() {
  return (
    <main className="min-h-screen bg-[#151617] text-white">
      <section className="mx-auto flex w-full max-w-5xl flex-col gap-10 px-6 py-16">
        <header className="space-y-4">
          <p className="text-xs uppercase tracking-[0.4em] text-white/60">BuyAnything</p>
          <h1 className="text-4xl font-semibold leading-tight text-white md:text-5xl">Guides</h1>
          <p className="max-w-2xl text-lg text-white/75">
            Practical sourcing playbooks for complex purchases — built for executives and the assistants who support them.
          </p>
        </header>

        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {GUIDES.map((guide) => (
            <Link
              key={guide.slug}
              href={`/guides/${guide.slug}`}
              className="group flex flex-col gap-3 rounded-2xl border border-white/10 bg-white/5 p-6 transition hover:border-white/20 hover:bg-white/[0.07]"
            >
              <span
                className={`w-fit rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide ${TAG_STYLES[guide.tag] || 'bg-white/10 text-white/70'}`}
              >
                {guide.tag}
              </span>
              <h2 className="text-sm font-semibold leading-snug text-white group-hover:text-white transition">
                {guide.title}
              </h2>
              <p className="text-xs text-white/55 leading-relaxed">{guide.desc}</p>
            </Link>
          ))}
        </div>
      </section>
    </main>
  );
}
