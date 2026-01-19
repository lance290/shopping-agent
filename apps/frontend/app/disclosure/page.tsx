import React from 'react';

export default function DisclosurePage() {
  return (
    <div className="max-w-2xl mx-auto p-8 bg-white min-h-screen">
      <h1 className="text-2xl font-bold mb-6 text-gray-900">Affiliate Disclosure</h1>
      
      <div className="prose prose-sm text-gray-700">
        <p className="mb-4">
          BuyAnything.ai participates in various affiliate marketing programs. This means that we may earn a commission 
          on purchases made through our links to retailer sites.
        </p>
        
        <h2 className="text-xl font-semibold mb-3 text-gray-900">How It Works</h2>
        <p className="mb-4">
          When you use our agent to find products, we search across multiple retailers to find options that match your 
          requirements. Some of the links we provide are "affiliate links." If you click on one of these links and 
          make a purchase, the retailer pays us a small percentage of the sale amount.
        </p>
        
        <h2 className="text-xl font-semibold mb-3 text-gray-900">Our Commitment to You</h2>
        <ul className="list-disc pl-5 mb-4 space-y-2">
          <li>
            <strong>No Extra Cost:</strong> Using our affiliate links does not increase the price you pay. 
            The price is the same whether you use our link or go directly to the retailer.
          </li>
          <li>
            <strong>Unbiased Recommendations:</strong> Our AI agent prioritizes finding the best match for your 
            needs (price, specs, shipping) over affiliate potential. We do not manually favor specific retailers 
            solely for higher commissions.
          </li>
          <li>
            <strong>Transparency:</strong> We clearly label our interface with this disclosure so you always know 
            how we are funded.
          </li>
        </ul>
        
        <p className="text-sm text-gray-500 mt-8 pt-4 border-t border-gray-200">
          Last updated: January 2026
        </p>
      </div>
    </div>
  );
}
