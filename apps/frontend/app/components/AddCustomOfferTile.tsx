import { useState } from 'react';
import { Plus, X } from 'lucide-react';
import { Card } from '../../components/ui/Card';
import { Button } from '../../components/ui/Button';
import { Input } from '../../components/ui/Input';
import { cn } from '../../utils/cn';

interface AddCustomOfferTileProps {
  onAdd: (offerData: {
    url: string;
    title?: string;
    price?: number;
    merchant?: string;
    imageUrl?: string;
  }) => void;
}

export default function AddCustomOfferTile({ onAdd }: AddCustomOfferTileProps) {
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [url, setUrl] = useState('');
  const [title, setTitle] = useState('');
  const [price, setPrice] = useState('');
  const [merchant, setMerchant] = useState('');
  const [imageUrl, setImageUrl] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    if (!url.trim()) {
      alert('URL is required');
      return;
    }

    // Validate URL format
    try {
      new URL(url.trim());
    } catch {
      alert('Please enter a valid URL');
      return;
    }

    const priceNum = price.trim() ? parseFloat(price.trim()) : undefined;
    if (price.trim() && (!priceNum || isNaN(priceNum) || priceNum < 0)) {
      alert('Please enter a valid price');
      return;
    }

    onAdd({
      url: url.trim(),
      title: title.trim() || undefined,
      price: priceNum,
      merchant: merchant.trim() || undefined,
      imageUrl: imageUrl.trim() || undefined,
    });

    // Reset form
    setUrl('');
    setTitle('');
    setPrice('');
    setMerchant('');
    setImageUrl('');
    setIsModalOpen(false);
  };

  const handleCancel = () => {
    setIsModalOpen(false);
    setUrl('');
    setTitle('');
    setPrice('');
    setMerchant('');
    setImageUrl('');
  };

  return (
    <>
      {/* Add Button Tile */}
      <button
        type="button"
        onClick={(e) => {
          e.stopPropagation();
          setIsModalOpen(true);
        }}
        className={cn(
          "flex-shrink-0 min-w-[255px] max-w-[255px] h-[450px]",
          "rounded-[12px] border-2 border-dashed border-warm-grey/60",
          "flex flex-col items-center justify-center",
          "bg-warm-light/30 hover:bg-warm-light/50",
          "transition-colors group cursor-pointer"
        )}
        title="Add custom URL"
      >
        <Plus size={32} className="text-onyx-muted mb-2 group-hover:text-onyx transition-colors" />
        <span className="text-sm font-semibold text-onyx-muted group-hover:text-onyx transition-colors">
          Add Custom URL
        </span>
      </button>

      {/* Modal */}
      {isModalOpen && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm"
          onClick={handleCancel}
        >
          <Card
            className="w-full max-w-md mx-4 bg-warm-light border-warm-grey"
            onClick={(e: React.MouseEvent) => e.stopPropagation()}
          >
            <div className="p-6">
              {/* Header */}
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-lg font-semibold text-onyx">Add Custom Offer</h2>
                <button
                  type="button"
                  onClick={handleCancel}
                  className="text-onyx-muted hover:text-onyx transition-colors"
                  aria-label="Close"
                >
                  <X size={20} />
                </button>
              </div>

              {/* Form */}
              <form onSubmit={handleSubmit} className="space-y-4">
                <div>
                  <label htmlFor="url" className="block text-sm font-medium text-onyx mb-1">
                    URL <span className="text-status-error">*</span>
                  </label>
                  <Input
                    id="url"
                    type="url"
                    value={url}
                    onChange={(e) => setUrl(e.target.value)}
                    placeholder="https://example.com/product"
                    required
                    className="bg-white border-warm-grey/60 text-onyx placeholder:text-onyx-muted"
                  />
                </div>

                <div>
                  <label htmlFor="title" className="block text-sm font-medium text-onyx mb-1">
                    Title (optional)
                  </label>
                  <Input
                    id="title"
                    type="text"
                    value={title}
                    onChange={(e) => setTitle(e.target.value)}
                    placeholder="Product name"
                    className="bg-white border-warm-grey/60 text-onyx placeholder:text-onyx-muted"
                  />
                </div>

                <div>
                  <label htmlFor="price" className="block text-sm font-medium text-onyx mb-1">
                    Price (optional)
                  </label>
                  <Input
                    id="price"
                    type="number"
                    step="0.01"
                    min="0"
                    value={price}
                    onChange={(e) => setPrice(e.target.value)}
                    placeholder="0.00"
                    className="bg-white border-warm-grey/60 text-onyx placeholder:text-onyx-muted"
                  />
                </div>

                <div>
                  <label htmlFor="merchant" className="block text-sm font-medium text-onyx mb-1">
                    Merchant (optional)
                  </label>
                  <Input
                    id="merchant"
                    type="text"
                    value={merchant}
                    onChange={(e) => setMerchant(e.target.value)}
                    placeholder="Store name"
                    className="bg-white border-warm-grey/60 text-onyx placeholder:text-onyx-muted"
                  />
                </div>

                <div>
                  <label htmlFor="imageUrl" className="block text-sm font-medium text-onyx mb-1">
                    Image URL (optional)
                  </label>
                  <Input
                    id="imageUrl"
                    type="url"
                    value={imageUrl}
                    onChange={(e) => setImageUrl(e.target.value)}
                    placeholder="https://example.com/image.jpg"
                    className="bg-white border-warm-grey/60 text-onyx placeholder:text-onyx-muted"
                  />
                </div>

                {/* Actions */}
                <div className="flex gap-3 pt-2">
                  <Button
                    type="button"
                    variant="ghost"
                    onClick={handleCancel}
                    className="flex-1"
                  >
                    Cancel
                  </Button>
                  <Button
                    type="submit"
                    variant="primary"
                    className="flex-1"
                  >
                    Add Offer
                  </Button>
                </div>
              </form>
            </div>
          </Card>
        </div>
      )}
    </>
  );
}
