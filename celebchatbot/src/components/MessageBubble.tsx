import { cn } from "@/lib/utils";
import { Message } from "@/data/celebrities";

interface MessageBubbleProps {
  message: Message;
  celebrityImage?: string;
}

const MessageBubble = ({ message, celebrityImage }: MessageBubbleProps) => {
  const isAI = message.sender === 'ai';

  return (
    <div
      className={cn(
        "flex items-end gap-2 animate-slide-up",
        isAI ? "justify-start" : "justify-end"
      )}
    >
      {isAI && (
        <div className="w-8 h-8 rounded-full overflow-hidden flex-shrink-0">
          <img
            src={celebrityImage || "https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?w=200&h=200&fit=crop&crop=faces"}
            alt="AI"
            className="w-full h-full object-cover object-center"
          />
        </div>
      )}

      <div
        className={cn(
          "max-w-[70%] px-4 py-3 rounded-2xl text-sm",
          isAI
            ? "bg-chat-ai text-white rounded-bl-md"
            : "bg-chat-user text-white rounded-br-md"
        )}
      >
        {message.text}
      </div>

      {!isAI && (
        <div className="w-8 h-8 rounded-full bg-primary/20 flex items-center justify-center flex-shrink-0">
          <span className="text-xs font-medium text-primary">You</span>
        </div>
      )}
    </div>
  );
};

export default MessageBubble;
