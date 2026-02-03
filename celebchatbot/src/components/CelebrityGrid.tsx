import { Hash } from "lucide-react";
import { celebrities, Celebrity } from "@/data/celebrities";
import CelebrityCard from "./CelebrityCard";

interface CelebrityGridProps {
  selectedCelebrity: Celebrity | null;
  onSelectCelebrity: (celebrity: Celebrity) => void;
}

const CelebrityGrid = ({ selectedCelebrity, onSelectCelebrity }: CelebrityGridProps) => {
  return (
    <section className="flex-1 flex flex-col h-screen bg-main-bg">
      {/* Header */}
      <header className="flex items-center justify-between px-6 py-4 bg-sidebar-bg/80 backdrop-blur-sm border-b border-border-dark">
        <div className="flex items-center gap-2">
          <Hash className="w-5 h-5 text-primary" />
          <h2 className="text-xl font-semibold text-white">Celebrities</h2>
        </div>
      </header>

      {/* Grid */}
      <div className="flex-1 overflow-y-auto scrollbar-thin p-6 pb-32">
        <div className="max-w-7xl mx-auto">
          <div className="grid grid-cols-4 gap-6">
            {celebrities.map((celebrity) => (
              <CelebrityCard
                key={celebrity.id}
                celebrity={celebrity}
                isSelected={selectedCelebrity?.id === celebrity.id}
                onClick={() => onSelectCelebrity(celebrity)}
              />
            ))}
          </div>
        </div>
      </div>
    </section>
  );
};

export default CelebrityGrid;
