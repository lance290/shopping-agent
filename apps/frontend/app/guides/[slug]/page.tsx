import { notFound } from 'next/navigation';
import Link from 'next/link';

// Simple content registry for the guides
const GUIDES = {
  'private-aviation': {
    title: 'Private aviation: charter vs. fractional vs. jet card',
    tag: 'Service',
    content: `
## The Cost-Benefit Thresholds

Evaluating private aviation options requires mapping your principal's exact flight profile against three distinct models.

### 1. On-Demand Charter (Under 25 hours/year)
The most flexible option, but subject to market pricing and availability. Best for ad-hoc trips or principals who rarely fly privately. You pay per trip, with no upfront capital commitment.

### 2. Jet Cards (25–50 hours/year)
Provides guaranteed availability and fixed hourly rates. You deposit funds upfront (typically $100k-$500k) and draw down as you fly. The key advantage is predictability — you know exactly what a trip will cost, avoiding peak-day surge pricing if booked within the contract window.

### 3. Fractional Ownership (50+ hours/year)
You purchase a share of a specific aircraft (e.g., 1/16th share = 50 hours). Involves a significant upfront capital cost, monthly management fees, and hourly flight rates. Provides the highest consistency in aircraft type and crew experience, plus potential tax depreciation benefits.
    `
  },
  'bespoke-menswear': {
    title: 'Sourcing bespoke menswear in 2025',
    tag: 'Luxury',
    content: `
## Navigating the bespoke process remotely

Sourcing true bespoke tailoring requires managing complex logistics, especially when the principal cannot travel for multiple fittings.

### Lead Times & Expectations
A first-time bespoke commission typically requires 3-4 fittings over 3-6 months. The pattern must be drafted from scratch. EAs must manage these expectations with principals used to off-the-rack immediacy.

### Trunk Shows vs. Studio Visits
Many top Savile Row and Neapolitan houses hold seasonal "trunk shows" in major cities (NY, LA, Tokyo). EAs should track these schedules. If the principal cannot attend, some houses offer "traveling tailors" who will visit the principal's home or office for an added premium.

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
    content: `
## Sourcing investment-grade art

Acquiring significant pieces requires navigating opaque markets and establishing credibility with galleries.

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
- Specialized fine art insurance riders
    `
  },
  'estate-automation': {
    title: 'Home automation for estate properties',
    tag: 'Service',
    content: `
## Scaling smart home tech for multi-structure estates

Consumer-grade smart home gear (Ring, Hue) fails at the estate scale. You need enterprise-grade systems.

### The Big Three Platforms
1. **Crestron:** The industry standard for massive estates. Highly customizable, incredibly robust, but requires specialized programmers for every change. Most expensive.
2. **Control4:** Excellent middle-ground. Very capable for large homes, slightly more modern interface than older Crestron setups, easier to find local integrators.
3. **Savant:** Strong focus on user interface and app design. Popular for modern luxury builds.

### The Importance of the Integrator
The hardware is secondary to the integrator (the company installing it). A poorly programmed Crestron system is worse than no system at all. 
- Vetting integrators requires checking references for similarly scaled properties.
- Ensure they provide a comprehensive ongoing support/maintenance contract (SLA).

### Network Backbone
Automation fails without perfect Wi-Fi. Estate networks require enterprise hardware (Ruckus, Cisco) and fiber-optic runs between outbuildings (guest houses, pool houses, gatehouses).
    `
  },
  'executive-relocation': {
    title: 'Executive relocation: vendor vetting checklist',
    tag: 'EA Guide',
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
- Climate-controlled (temperature and humidity)
- Art-facility grade security
- Bonded and insured

### Vehicle Transport
Exotic and vintage vehicles require specialized enclosed transport. Verify the transport company uses hard-sided enclosed trailers with hydraulic lift gates (not standard ramps, which can damage low-clearance cars).
    `
  },
  'luxury-vehicles': {
    title: 'Luxury vehicle acquisition: new vs. pre-owned exotics',
    tag: 'Luxury',
    content: `
## Sourcing high-end and exotic vehicles

Acquiring exotics involves navigating waitlists, dealer markups, and complex provenance issues.

### The "New" Exotic Game
Buying a new Ferrari or Porsche GT car isn't about having the money; it's about having the allocation.
- **Relationship Building:** Dealers reward repeat buyers. A new principal may need to buy less desirable models to get an allocation for a limited-production car.
- **Market Adjustments (ADM):** "Additional Dealer Markup" is common. Negotiating this requires knowing the current secondary market premium for that specific model.

### Pre-Owned & Auctions
The secondary market offers immediate gratification but carries risk.
- **CPO (Certified Pre-Owned):** The safest route for modern exotics, offering factory warranties.
- **Auctions (Bring a Trailer, RM Sotheby's):** Excellent for vintage or ultra-rare cars. EAs must arrange independent Pre-Purchase Inspections (PPI) *before* the principal bids.

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

  // Very basic markdown parsing for this simple guide format
  const parsedContent = guide.content
    .split('\n\n')
    .map(block => {
      if (block.startsWith('### ')) return \`<h3 class="text-lg font-semibold text-onyx mt-8 mb-4">\${block.replace('### ', '')}</h3>\`;
      if (block.startsWith('## ')) return \`<h2 class="text-2xl font-semibold text-white mt-12 mb-6">\${block.replace('## ', '')}</h2>\`;
      if (block.startsWith('- ')) {
        const items = block.split('\n').map(item => \`<li class="ml-4 list-disc text-onyx/80">\${item.replace('- ', '')}</li>\`).join('');
        return \`<ul class="mb-4">\${items}</ul>\`;
      }
      return \`<p class="text-onyx/80 leading-relaxed mb-4">\${block}</p>\`;
    })
    .join('')
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');

  return (
    <main className="min-h-screen bg-canvas text-onyx">
      <nav className="border-b border-warm-grey/30 bg-canvas sticky top-0 z-10">
        <div className="mx-auto flex h-14 max-w-4xl items-center px-6">
          <Link href="/" className="text-sm font-semibold hover:text-agent-blurple transition-colors">
            ← Back to Board
          </Link>
        </div>
      </nav>

      <article className="mx-auto max-w-3xl px-6 py-16">
        <header className="mb-12">
          <span className="inline-block rounded-full bg-agent-blurple/15 px-3 py-1 text-xs font-semibold uppercase tracking-wide text-agent-camel mb-6">
            {guide.tag}
          </span>
          <h1 className="text-3xl md:text-5xl font-semibold leading-tight text-white mb-6">
            {guide.title}
          </h1>
          <div className="flex items-center gap-4 text-sm text-onyx-muted border-t border-b border-warm-grey/30 py-4">
            <div className="flex items-center gap-2">
              <div className="w-6 h-6 rounded-full bg-gradient-to-br from-agent-blurple to-agent-camel flex items-center justify-center text-[10px] text-white font-bold">BA</div>
              <span>BuyAnything Research Team</span>
            </div>
            <span>·</span>
            <span>4 min read</span>
          </div>
        </header>

        <div dangerouslySetInnerHTML={{ __html: parsedContent }} />

        <div className="mt-16 p-8 rounded-2xl bg-warm-light border border-warm-grey/50 text-center">
          <h3 className="text-xl font-semibold text-white mb-3">Ready to start sourcing?</h3>
          <p className="text-sm text-onyx-muted mb-6 max-w-md mx-auto">
            Let the agent handle the legwork. Set your requirements and compare real options in one place.
          </p>
          <Link href="/login" className="btn-primary inline-flex">
            Start a request
          </Link>
        </div>
      </article>
    </main>
  );
}
