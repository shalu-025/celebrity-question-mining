import { useNavigate } from "react-router-dom";
import Sidebar from "@/components/Sidebar";
import CelebrityGrid from "@/components/CelebrityGrid";
import SearchBar from "@/components/SearchBar";
import { Celebrity, celebrities } from "@/data/celebrities";

const Index = () => {
  const navigate = useNavigate();

  const handleSearch = (query: string) => {
    // Check if celebrity exists in our list
    const existingCelebrity = celebrities.find(
      (c) => c.name.toLowerCase().includes(query.toLowerCase())
    );

    if (existingCelebrity) {
      navigate(`/celebrity/${existingCelebrity.id}`);
    } else {
      // Create a new celebrity with random image for search
      const randomImages = [
        "https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?w=600&h=800&fit=crop&crop=faces",
        "https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=600&h=800&fit=crop&crop=faces",
        "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=600&h=800&fit=crop&crop=faces",
        "https://images.unsplash.com/photo-1500648767791-00dcc994a43e?w=600&h=800&fit=crop&crop=faces",
        "https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=600&h=800&fit=crop&crop=faces",
        "https://images.unsplash.com/photo-1531123897727-8f129e1688ce?w=600&h=800&fit=crop&crop=faces",
        "https://images.unsplash.com/photo-1544005313-94ddf0286df2?w=600&h=800&fit=crop&crop=faces",
        "https://images.unsplash.com/photo-1506794778202-cad84cf45f1d?w=600&h=800&fit=crop&crop=faces"
      ];

      const newCelebrity: Celebrity = {
        id: Date.now(),
        name: query,
        image: randomImages[Math.floor(Math.random() * randomImages.length)],
        views: "0",
        likes: "0",
        badge: "New Search",
        bio: `AI-generated character for "${query}"`,
        tags: ["Search", "New"],
        creator: "system"
      };

      // Add to celebrities list temporarily
      celebrities.push(newCelebrity);
      navigate(`/celebrity/${newCelebrity.id}`);
    }
  };

  const handleSelectCelebrity = (celebrity: Celebrity) => {
    navigate(`/celebrity/${celebrity.id}`);
  };

  return (
    <div className="flex min-h-screen">
      {/* Left Sidebar - 15% */}
      <Sidebar />

      {/* Main Content Area - Full Width */}
      <div className="ml-[15%] flex-1">
        <CelebrityGrid
          selectedCelebrity={null}
          onSelectCelebrity={handleSelectCelebrity}
        />
      </div>

      {/* Fixed Bottom Search Bar */}
      <SearchBar onSearch={handleSearch} />
    </div>
  );
};

export default Index;
