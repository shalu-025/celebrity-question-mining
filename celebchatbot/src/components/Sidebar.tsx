import { Home, Sparkles, MessageCircle, Users } from "lucide-react";

const Sidebar = () => {
  return (
    <aside className="fixed left-0 top-0 h-screen w-[15%] bg-sidebar-bg border-r border-border-dark flex flex-col py-6 px-4">
      {/* Logo */}
      <div className="mb-10">
        <h1 className="text-2xl font-bold text-white tracking-tight">
          <span className="text-primary">talkie talkie</span>
        </h1>
        <p className="text-xs text-white/50 mt-2">Chat with AI celebrities</p>
      </div>

      {/* Navigation */}
      <nav className="mb-8">
        <button className="w-full flex items-center gap-3 px-4 py-3 rounded-lg bg-secondary/10 text-white hover:bg-secondary/20 transition-colors">
          <Home className="w-5 h-5" />
          <span className="font-medium">Home</span>
        </button>
      </nav>

      {/* Features Section */}
      <div className="flex-1 space-y-6">
        <div>
          <h3 className="text-sm font-semibold text-white/80 mb-4 flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-primary" />
            Features
          </h3>
          <div className="space-y-3">
            <div className="flex items-start gap-2">
              <MessageCircle className="w-4 h-4 text-primary/70 mt-0.5 flex-shrink-0" />
              <p className="text-xs text-white/60 leading-relaxed">
                Chat with AI versions of your favorite celebrities
              </p>
            </div>
            <div className="flex items-start gap-2">
              <Users className="w-4 h-4 text-primary/70 mt-0.5 flex-shrink-0" />
              <p className="text-xs text-white/60 leading-relaxed">
                Explore personalities from entertainment to tech
              </p>
            </div>
            <div className="flex items-start gap-2">
              <Sparkles className="w-4 h-4 text-primary/70 mt-0.5 flex-shrink-0" />
              <p className="text-xs text-white/60 leading-relaxed">
                Get unique responses powered by AI
              </p>
            </div>
          </div>
        </div>

        {/* About Section */}
        <div className="pt-6 border-t border-border-dark/50">
          <h3 className="text-xs font-semibold text-white/80 mb-2">About</h3>
          <p className="text-xs text-white/50 leading-relaxed">
            Experience conversations with AI-generated celebrity personalities.
            Each chat is unique and engaging.
          </p>
        </div>
      </div>

      {/* Version Info */}
      <div className="mt-auto pt-4 border-t border-border-dark/50">
        <p className="text-xs text-white/40">v1.0.0</p>
      </div>
    </aside>
  );
};

export default Sidebar;
