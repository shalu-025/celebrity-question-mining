import { useState, useRef, useEffect } from "react";
import { Send } from "lucide-react";
import { Celebrity, Message, getInitialMessages } from "@/data/celebrities";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import MessageBubble from "./MessageBubble";

interface ChatPanelProps {
  celebrity: Celebrity | null;
  searchQuery?: string | null;
}

const ChatPanel = ({ celebrity, searchQuery }: ChatPanelProps) => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputValue, setInputValue] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (celebrity) {
      if (searchQuery && celebrity.id === -1) {
        // This is a search query, show a custom response
        const searchMessage: Message = {
          id: Date.now(),
          sender: 'ai',
          text: `I'd be happy to help you with "${searchQuery}". What would you like to know?`,
          timestamp: new Date()
        };
        setMessages([searchMessage]);
      } else {
        setMessages(getInitialMessages(celebrity.id));
      }
    }
  }, [celebrity, searchQuery]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSend = () => {
    if (!inputValue.trim() || !celebrity) return;

    const userMessage: Message = {
      id: Date.now(),
      sender: 'user',
      text: inputValue,
      timestamp: new Date()
    };

    setMessages(prev => [...prev, userMessage]);
    setInputValue("");
    setIsTyping(true);

    // Simulate AI response
    setTimeout(() => {
      const aiResponses = [
        "That's such an interesting perspective! Tell me more.",
        "I appreciate you sharing that with me.",
        "You know, I've been thinking about that too lately.",
        "That reminds me of something from my latest project...",
        "I love connecting with fans like you!"
      ];
      
      const aiMessage: Message = {
        id: Date.now() + 1,
        sender: 'ai',
        text: aiResponses[Math.floor(Math.random() * aiResponses.length)],
        timestamp: new Date()
      };
      
      setMessages(prev => [...prev, aiMessage]);
      setIsTyping(false);
    }, 1500);
  };

  if (!celebrity) {
    return (
      <div className="w-[40%] h-screen bg-chat-bg flex items-center justify-center">
        <div className="text-center animate-fade-in">
          <div className="w-48 h-48 mx-auto mb-6 rounded-full overflow-hidden ring-4 ring-primary/20">
            <img
              src="https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=600&h=600&fit=crop&crop=faces"
              alt="Chat assistant"
              className="w-full h-full object-cover object-center"
            />
          </div>
          <h2 className="text-2xl font-bold mb-2 bg-gradient-to-r from-primary via-purple-400 to-primary bg-clip-text text-transparent">
            Select a celebrity to chat
          </h2>
          <p className="text-sm text-muted-foreground">Choose from the grid on the left</p>
        </div>
      </div>
    );
  }

  return (
    <div className="w-[40%] h-screen bg-chat-bg flex flex-col animate-fade-in">
      {/* Profile Header - Simplified */}
      <div className="p-6 border-b border-border bg-white">
        <div className="flex items-center gap-4">
          <div className="w-24 h-24 rounded-full overflow-hidden ring-4 ring-primary/20">
            <img
              src={celebrity.image}
              alt={celebrity.name}
              className="w-full h-full object-cover object-center"
            />
          </div>

          <div className="flex-1">
            <h2 className="text-xl font-bold text-foreground">{celebrity.name}</h2>
            <p className="text-xs text-muted-foreground">AI-generated character</p>
          </div>
        </div>
      </div>

      {/* Bio Card */}
      <div className="mx-4 mt-4 p-4 bg-chat-info rounded-xl">
        <p className="text-sm text-foreground/80 italic">"{celebrity.bio}"</p>
      </div>

      {/* Chat Messages */}
      <ScrollArea className="flex-1 px-4 py-4">
        <div className="space-y-4">
          {messages.map((message) => (
            <MessageBubble
              key={message.id}
              message={message}
              celebrityImage={celebrity.image}
            />
          ))}
          
          {isTyping && (
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-full overflow-hidden">
                <img src={celebrity.image} alt="" className="w-full h-full object-cover object-center" />
              </div>
              <div className="bg-chat-ai text-white px-4 py-3 rounded-2xl rounded-bl-md">
                <div className="flex gap-1">
                  <span className="w-2 h-2 bg-white/60 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                  <span className="w-2 h-2 bg-white/60 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                  <span className="w-2 h-2 bg-white/60 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                </div>
              </div>
            </div>
          )}
          
          <div ref={messagesEndRef} />
        </div>
      </ScrollArea>

      {/* Message Input */}
      <div className="p-4 border-t border-border bg-white">
        <div className="flex items-center gap-2">
          <Input
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSend()}
            placeholder={`Message ${celebrity.name}...`}
            className="flex-1 bg-secondary/50 border-0"
          />

          <Button
            onClick={handleSend}
            size="icon"
            className="rounded-full bg-primary hover:bg-primary/90"
            disabled={!inputValue.trim()}
          >
            <Send className="w-4 h-4" />
          </Button>
        </div>
      </div>
    </div>
  );
};

export default ChatPanel;
