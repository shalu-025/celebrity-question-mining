import { useState, useRef, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { Send, ArrowLeft } from "lucide-react";
import { celebrities, Celebrity, Message, getInitialMessages } from "@/data/celebrities";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import MessageBubble from "@/components/MessageBubble";
import { sendChatMessage } from "@/services/api";

const CelebrityDetail = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const [celebrity, setCelebrity] = useState<Celebrity | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputValue, setInputValue] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const foundCelebrity = celebrities.find((c) => c.id === Number(id));
    if (foundCelebrity) {
      setCelebrity(foundCelebrity);
      setMessages(getInitialMessages(foundCelebrity.id));
    }
  }, [id]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSend = async () => {
    if (!inputValue.trim() || !celebrity) return;

    const userMessage: Message = {
      id: Date.now(),
      sender: 'user',
      text: inputValue,
      timestamp: new Date()
    };

    // Add user message to chat
    setMessages(prev => [...prev, userMessage]);
    const questionText = inputValue; // Save before clearing
    setInputValue("");
    setIsTyping(true);

    try {
      // Call the real backend API
      // This sends: celebrity_name="Virat Kohli" (or whoever was clicked)
      //            question="What inspires you?" (or whatever user typed)
      // Backend runs: python main.py --celebrity "..." --question "..."
      const response = await sendChatMessage(celebrity.name, questionText);

      // Create AI response message
      const aiMessage: Message = {
        id: Date.now() + 1,
        sender: 'ai',
        text: response.answer || "I'm having trouble connecting right now. Please try again!",
        timestamp: new Date()
      };

      setMessages(prev => [...prev, aiMessage]);
    } catch (error) {
      console.error('Failed to get response:', error);

      // Show error message to user
      const errorMessage: Message = {
        id: Date.now() + 1,
        sender: 'ai',
        text: "Sorry, I'm having trouble connecting to the server. Please make sure the backend is running!",
        timestamp: new Date()
      };

      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsTyping(false);
    }
  };

  if (!celebrity) {
    return (
      <div className="min-h-screen bg-main-bg flex items-center justify-center">
        <div className="text-center">
          <p className="text-white text-xl">Celebrity not found</p>
          <Button onClick={() => navigate("/")} className="mt-4">
            Go Back
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen bg-main-bg">
      {/* Back Button - Top Left */}
      <button
        onClick={() => navigate("/")}
        className="fixed top-4 left-4 z-50 p-3 rounded-full bg-sidebar-bg/80 backdrop-blur-sm border border-border-dark text-white hover:bg-sidebar-bg transition-colors"
      >
        <ArrowLeft className="w-5 h-5" />
      </button>

      {/* Left Side - Celebrity Image */}
      <div className="w-1/3 relative">
        <div className="fixed left-0 top-0 w-1/3 h-screen">
          <img
            src={celebrity.image}
            alt={celebrity.name}
            className="w-full h-full object-cover object-top"
          />
          <div className="absolute inset-0 bg-gradient-to-r from-black/60 to-transparent" />

          {/* Celebrity Info Overlay */}
          <div className="absolute bottom-0 left-0 right-0 p-8 text-white">
            <span className="inline-block px-3 py-1 text-xs font-semibold bg-primary rounded-full mb-4">
              {celebrity.badge}
            </span>
            <h1 className="text-4xl font-bold mb-2">{celebrity.name}</h1>
            <p className="text-sm text-white/80 mb-4">{celebrity.bio}</p>
            <div className="flex gap-2">
              {celebrity.tags.map((tag, index) => (
                <span key={index} className="px-2 py-1 text-xs bg-white/20 backdrop-blur-sm rounded-full">
                  {tag}
                </span>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Right Side - Chat Interface */}
      <div className="flex-1 flex flex-col">
        {/* Chat Header */}
        <div className="px-8 py-6 border-b border-border-dark bg-sidebar-bg/50 backdrop-blur-sm">
          <div className="flex items-center gap-4">
            <div className="w-16 h-16 rounded-full overflow-hidden ring-4 ring-primary/20">
              <img
                src={celebrity.image}
                alt={celebrity.name}
                className="w-full h-full object-cover object-center"
              />
            </div>
            <div>
              <h2 className="text-2xl font-bold text-white">{celebrity.name}</h2>
              <p className="text-sm text-white/60">AI-generated character</p>
            </div>
          </div>
        </div>

        {/* Chat Messages */}
        <ScrollArea className="flex-1 px-8 py-6">
          <div className="max-w-4xl mx-auto space-y-4">
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
        <div className="px-8 py-6 border-t border-border-dark bg-sidebar-bg/50 backdrop-blur-sm">
          <div className="max-w-4xl mx-auto flex items-center gap-2">
            <Input
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSend()}
              placeholder={`Message ${celebrity.name}...`}
              className="flex-1 bg-main-bg/50 border-border-dark text-white placeholder:text-white/40"
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
    </div>
  );
};

export default CelebrityDetail;
