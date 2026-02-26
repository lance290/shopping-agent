import { notFound } from 'next/navigation';
import Link from 'next/link';
import ContactForm from '../../components/ContactForm';

// Richer content registry with images and better formatting
const GUIDES = {
  'private-aviation': {
    title: 'Private aviation: charter vs. fractional vs. jet card',
    tag: 'Service',
    heroImage: 'https://images.unsplash.com/photo-1540962351504-03099e0a754b?auto=format&fit=crop&w=2000&q=80',
    content: `
## The Cost-Benefit Thresholds

Evaluating private aviation options requires mapping your principal's exact flight profile against three distinct models. Making the wrong choice here can easily result in a six-figure annual inefficiency.

![Cabin Interior](https://images.unsplash.com/photo-1543226998-320c242f2b38?auto=format&fit=crop&w=1200&q=80)

### 1. On-Demand Charter (Under 25 hours/year)
The most flexible option, but subject to market pricing and availability. Best for ad-hoc trips or principals who rarely fly privately. 
- You pay per trip, with no upfront capital commitment.
- Pricing fluctuates wildly around peak holidays.
- Aircraft consistency cannot be guaranteed.

### 2. Jet Cards (25–50 hours/year)
Provides guaranteed availability and fixed hourly rates. You deposit funds upfront (typically $100k-$500k) and draw down as you fly. 
- The key advantage is predictability — you know exactly what a trip will cost.
- Avoids peak-day surge pricing if booked within the contract window.
- Often guarantees a specific aircraft class (e.g., Light Jet, Super Midsize).

### 3. Fractional Ownership (50+ hours/year)
You purchase a share of a specific aircraft (e.g., 1/16th share = 50 hours). Involves a significant upfront capital cost, monthly management fees, and hourly flight rates. 
- Provides the highest consistency in aircraft type and crew experience.
- Strong potential tax depreciation benefits for business use.
- Highest barrier to entry, but lowest hourly operating cost at volume.
    `
  },
  'bespoke-menswear': {
    title: 'Sourcing bespoke menswear in 2025',
    tag: 'Luxury',
    heroImage: 'https://images.unsplash.com/photo-1593030103066-0093718efeb9?auto=format&fit=crop&w=2000&q=80',
    content: `
## Navigating the bespoke process remotely

Sourcing true bespoke tailoring requires managing complex logistics, especially when the principal cannot travel for multiple fittings.

![Tailor Working](https://images.unsplash.com/photo-1598808503746-f34c53b9323e?auto=format&fit=crop&w=1200&q=80)

### Lead Times & Expectations
A first-time bespoke commission typically requires 3-4 fittings over 3-6 months. The pattern must be drafted from scratch. EAs must manage these expectations with principals used to off-the-rack immediacy.

### Trunk Shows vs. Studio Visits
Many top Savile Row and Neapolitan houses hold seasonal "trunk shows" in major cities (NY, LA, Tokyo). EAs should track these schedules. 
- If the principal cannot attend, some houses offer "traveling tailors" who will visit the principal's home or office for an added premium.
- Always secure the master cutter, not a junior representative, for the initial measuring.

### Managing the Details
Keep meticulous records of:
- Chosen fabrics (mill, weight, composition)
- Styling details (lapel width, button stance, lining)
- Completed garments (for future remote re-ordering)
    `
  },
  'art-acquisition': {
    title: 'Art acquisition for new collectors',
    tag: 'Luxury',
    heroImage: 'https://images.unsplash.com/photo-1544413158-b64db6e64ec6?auto=format&fit=crop&w=2000&q=80',
    content: `
## Sourcing investment-grade art

Acquiring significant pieces requires navigating opaque markets and establishing credibility with galleries.

![Gallery Exhibition](https://images.unsplash.com/photo-1518998053901-5348d3961a04?auto=format&fit=crop&w=1200&q=80)

### Primary vs. Secondary Market
**Primary Market:** Buying directly from a gallery representing the artist. Prices are fixed, but access to top works is highly restricted. Galleries prioritize established collectors to protect the artist's market.

**Secondary Market:** Buying at auction (Sotheby's, Christie's) or through private dealers. Prices are market-driven and transparent, but include significant buyer's premiums (up to 25%).

### The Role of an Art Advisor
For six-figure acquisitions, an independent art advisor is crucial. They provide:
- Market analysis and valuation
- Access to primary market waiting lists
- Negotiation leverage
- Condition reporting and authentication management

### Logistics & Insurance
Never overlook the physical reality of the piece:
- Crating and climate-controlled transport
- Installation engineering (weight loads, UV protection)
- Specialized fine art insurance riders must be bound *before* transport begins
    `
  },
  'estate-automation': {
    title: 'Home automation for estate properties',
    tag: 'Service',
    heroImage: 'https://images.unsplash.com/photo-1558002038-1055907df827?auto=format&fit=crop&w=2000&q=80',
    content: `
## Scaling smart home tech for multi-structure estates

Consumer-grade smart home gear (Ring, Hue) fails at the estate scale. You need enterprise-grade systems.

### The Big Three Platforms
**1. Crestron:** The industry standard for massive estates. Highly customizable, incredibly robust, but requires specialized programmers for every change. Most expensive.

**2. Control4:** Excellent middle-ground. Very capable for large homes, slightly more modern interface than older Crestron setups, easier to find local integrators.

**3. Savant:** Strong focus on user interface and app design. Popular for modern luxury builds and Apple-ecosystem users.

### The Importance of the Integrator
The hardware is secondary to the integrator (the company installing it). A poorly programmed Crestron system is worse than no system at all. 
- Vetting integrators requires checking references for similarly scaled properties.
- Ensure they provide a comprehensive ongoing support/maintenance contract (SLA) with guaranteed response times.

### Network Backbone
Automation fails without perfect Wi-Fi. Estate networks require enterprise hardware (Ruckus, Cisco) and fiber-optic runs between outbuildings (guest houses, pool houses, gatehouses).
    `
  },
  'executive-relocation': {
    title: 'Executive relocation: vendor vetting checklist',
    tag: 'EA Guide',
    heroImage: 'https://images.unsplash.com/photo-1560448204-e02f11c3d0e2?auto=format&fit=crop&w=2000&q=80',
    content: `
## Managing white-glove household transitions

Relocating an executive involves high-value fragile items, extreme privacy requirements, and zero tolerance for delays.

### Vetting Moving Firms
Do not use standard commercial movers. You need "white-glove" fine art and antique specialists.
- **Verification:** Are their crews full-time employees with background checks, or day-labor contractors?
- **Insurance:** Request their certificate of insurance (COI) and verify coverage limits for single high-value items.
- **Custom Crating:** Do they build custom wooden crates on-site for art, chandeliers, and pianos?

### Secure Storage Logistics
If there is a gap between homes, storage must be:
- Climate-controlled (temperature and humidity logged)
- Art-facility grade security (biometric access, 24/7 guard)
- Bonded and insured

### Vehicle Transport
Exotic and vintage vehicles require specialized enclosed transport. Verify the transport company uses hard-sided enclosed trailers with hydraulic lift gates (not standard ramps, which can damage low-clearance cars).
    `
  },
  'luxury-vehicles': {
    title: 'Luxury vehicle acquisition: new vs. pre-owned exotics',
    tag: 'Luxury',
    heroImage: 'https://images.unsplash.com/photo-1603584173870-7f23fdae1b7a?auto=format&fit=crop&w=2000&q=80',
    content: `
## Sourcing high-end and exotic vehicles

Acquiring exotics involves navigating waitlists, dealer markups, and complex provenance issues.

![Porsche Detail](https://images.unsplash.com/photo-1503376713175-684c7a6e14ed?auto=format&fit=crop&w=1200&q=80)

### The "New" Exotic Game
Buying a new Ferrari or Porsche GT car isn't about having the money; it's about having the allocation.
- **Relationship Building:** Dealers reward repeat buyers. A new principal may need to buy less desirable models to get an allocation for a limited-production car.
- **Market Adjustments (ADM):** "Additional Dealer Markup" is common. Negotiating this requires knowing the current secondary market premium for that specific model.

### Pre-Owned & Auctions
The secondary market offers immediate gratification but carries risk.
- **CPO (Certified Pre-Owned):** The safest route for modern exotics, offering factory warranties.
- **Auctions:** Excellent for vintage or ultra-rare cars. EAs must arrange independent Pre-Purchase Inspections (PPI) *before* the principal bids.

### Independent Inspections
Never buy an exotic without a PPI from an independent specialist (not the selling dealer). A $1,500 inspection can save $50,000 in hidden engine or chassis issues.
    `
  }
};

export default function GuidePage({ params }: { params: { slug: string } }) {
  const guide = GUIDES[params.slug as keyof typeof GUIDES];

  if (!guide) {
    notFound();
  }

  // Enhanced markdown parsing to handle images
  const parsedContent = guide.content
    .split('\n\n')
    .map(block => {
      block = block.trim();
      if (!block) return '';
      if (block.startsWith('![')) {
        const altMatch = block.match(/!\[(.*?)\]/);
        const urlMatch = block.match(/\((.*?)\)/);
        if (altMatch && urlMatch) {
          return \`<figure class="my-10"><img src="\${urlMatch[1]}" alt="\${altMatch[1]}" class="w-full rounded-2xl border border-white/10" /><figcaption class="text-center text-xs text-onyx-muted mt-3">\${altMatch[1]}</figcaption></figure>\`;
        }
      }
      if (block.startsWith('### ')) return \`<h3 class="text-xl font-semibold text-white mt-12 mb-4">\${block.replace('### ', '')}</h3>\`;
      if (block.startsWith('## ')) return \`<h2 class="text-2xl font-bold text-white mt-14 mb-6 border-b border-white/10 pb-4">\${block.replace('## ', '')}</h2>\`;
      if (block.startsWith('- ')) {
        const items = block.split('\n').map(item => \`<li class="ml-6 list-disc text-onyx/80 py-1">\${item.replace('- ', '').replace(/\*\*(.*?)\*\*/g, '<strong class="text-white">$1</strong>')}</li>\`).join('');
        return \`<ul class="mb-6 space-y-1">\${items}</ul>\`;
      }
      return \`<p class="text-onyx/80 leading-relaxed mb-6 text-lg">\${block.replace(/\*\*(.*?)\*\*/g, '<strong class="text-white">$1</strong>')}</p>\`;
    })
    .join('');

  return (
    <main className="min-h-screen bg-canvas text-onyx pb-24">
      <nav className="border-b border-warm-grey/30 bg-canvas/80 backdrop-blur-md sticky top-0 z-10">
        <div className="mx-auto flex h-16 max-w-5xl items-center px-6">
          <Link href="/" className="text-sm font-semibold hover:text-agent-blurple transition-colors flex items-center gap-2">
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
            </svg>
            Back to Dashboard
          </Link>
        </div>
      </nav>

      <article className="mx-auto max-w-3xl px-6 pt-12">
        <header className="mb-14 text-center">
          <span className="inline-block rounded-full bg-agent-blurple/15 px-3 py-1.5 text-xs font-bold uppercase tracking-widest text-agent-camel mb-6 border border-agent-blurple/20">
            {guide.tag}
          </span>
          <h1 className="text-4xl md:text-5xl lg:text-6xl font-bold leading-tight text-white mb-8 tracking-tight">
            {guide.title}
          </h1>
          <div className="flex items-center justify-center gap-4 text-sm text-onyx-muted border-y border-warm-grey/30 py-4 max-w-md mx-auto">
            <div className="flex items-center gap-2">
              <div className="w-6 h-6 rounded-full bg-gradient-to-br from-agent-blurple to-agent-camel flex items-center justify-center text-[10px] text-white font-bold">BA</div>
              <span className="font-medium text-onyx/90">BuyAnything Concierge</span>
            </div>
            <span>·</span>
            <span>4 min read</span>
          </div>
        </header>

        {guide.heroImage && (
          <div className="w-full aspect-[21/9] rounded-3xl overflow-hidden mb-16 border border-white/10 shadow-2xl">
            <img src={guide.heroImage} alt="Hero" className="w-full h-full object-cover" />
          </div>
        )}

        <div 
          className="prose prose-invert max-w-none mb-24 font-serif text-lg"
          dangerouslySetInnerHTML={{ __html: parsedContent }}
        />

        <hr className="border-warm-grey/30 mb-16" />

        <div id="contact-concierge" className="scroll-mt-24">
          <ContactForm />
        </div>
      </article>
    </main>
  );
}
