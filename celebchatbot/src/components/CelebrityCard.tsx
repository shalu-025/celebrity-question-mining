import { Celebrity } from "@/data/celebrities";
import { cn } from "@/lib/utils";

interface CelebrityCardProps {
  celebrity: Celebrity;
  isSelected: boolean;
  onClick: () => void;
}

const CelebrityCard = ({ celebrity, isSelected, onClick }: CelebrityCardProps) => {
  return (
    <div
      onClick={onClick}
      className={cn(
        "relative h-[320px] rounded-xl overflow-hidden cursor-pointer transition-all duration-200 group",
        "hover:scale-[1.02] hover:shadow-[0_8px_30px_rgba(139,92,246,0.3)]",
        isSelected && "ring-2 ring-primary shadow-[0_0_20px_rgba(139,92,246,0.4)]"
      )}
    >
      {/* Background Image */}
      <div className="absolute inset-0 transition-transform duration-300 group-hover:scale-105">
        <img
          src={celebrity.image}
          alt={celebrity.name}
          className="w-full h-full object-cover object-top"
        />
      </div>

      {/* Gradient Overlay */}
      <div className="absolute inset-0 bg-gradient-to-t from-black/90 via-black/40 to-transparent" />

      {/* Badge */}
      <div className="absolute top-3 left-3">
        <span className="px-2 py-1 text-[10px] font-semibold bg-accent text-accent-foreground rounded-full">
          {celebrity.badge}
        </span>
      </div>

      {/* Content */}
      <div className="absolute bottom-0 left-0 right-0 p-4">
        <h3 className="text-lg font-bold text-white mb-2 truncate">
          {celebrity.name}
        </h3>

        <p className="text-xs text-white/60 line-clamp-2">
          {celebrity.bio}
        </p>
      </div>
    </div>
  );
};

export default CelebrityCard;
