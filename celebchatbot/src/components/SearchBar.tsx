import { useState } from "react";
import { Search, Send } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";

interface SearchBarProps {
  onSearch: (query: string) => void;
}

const SearchBar = ({ onSearch }: SearchBarProps) => {
  const [query, setQuery] = useState("");

  const handleSubmit = () => {
    if (!query.trim()) return;
    onSearch(query.trim());
    setQuery("");
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleSubmit();
    }
  };

  return (
    <div className="fixed bottom-0 left-[15%] right-0 z-50 bg-sidebar-bg/95 backdrop-blur-md border-t border-border-dark">
      <div className="px-6 py-4 max-w-7xl mx-auto">
        <div className="flex items-center gap-3 bg-main-bg/80 rounded-full px-4 py-2 border border-border-dark">
          <Search className="w-5 h-5 text-muted-foreground flex-shrink-0" />
          <Input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Search for a celebrity or ask a question..."
            className="flex-1 bg-transparent border-0 focus-visible:ring-0 focus-visible:ring-offset-0 text-white placeholder:text-muted-foreground"
          />
          <Button
            onClick={handleSubmit}
            size="icon"
            className="rounded-full bg-primary hover:bg-primary/90 flex-shrink-0"
            disabled={!query.trim()}
          >
            <Send className="w-4 h-4" />
          </Button>
        </div>
        <p className="text-xs text-muted-foreground text-center mt-2">
          Can't find who you're looking for? Type their name or ask any question!
        </p>
      </div>
    </div>
  );
};

export default SearchBar;
