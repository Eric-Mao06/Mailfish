'use client';

import { useState, useRef } from "react";

export default function Home() {
  const [personName, setPersonName] = useState("");
  const [messages, setMessages] = useState<Array<{ role: 'user' | 'assistant', content: string }>>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isCloneReady, setIsCloneReady] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  const handleCreateClone = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    
    try {
      const response = await fetch('http://localhost:5000/create-clone', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json',
        },
        credentials: 'include',
        mode: 'cors',
        body: JSON.stringify({ name: personName }),
      });
      
      if (!response.ok) throw new Error('Failed to create clone');
      
      const data = await response.json();
      if (data.success) {
        setIsCloneReady(true);
        setMessages([]);
      } else {
        throw new Error(data.message || 'Failed to create clone');
      }
    } catch (error) {
      console.error('Error creating clone:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const generateSpeech = async (text: string) => {
    try {
      setIsSpeaking(true);
      const response = await fetch('http://localhost:5000/text-to-speech', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ name: personName, text })
      });

      if (!response.ok) {
        throw new Error('Failed to generate speech');
      }

      const audioBlob = await response.blob();
      const audioUrl = URL.createObjectURL(audioBlob);
      
      if (audioRef.current) {
        audioRef.current.pause();
        audioRef.current.src = audioUrl;
        await audioRef.current.play();
      } else {
        const audio = new Audio(audioUrl);
        audioRef.current = audio;
        await audio.play();
      }

      audioRef.current.onended = () => {
        setIsSpeaking(false);
        URL.revokeObjectURL(audioUrl);
      };
    } catch (error) {
      console.error('Error generating speech:', error);
      setIsSpeaking(false);
    }
  };

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    const messageInput = (e.target as HTMLFormElement).message as HTMLInputElement;
    const message = messageInput.value.trim();
    
    if (!message) return;
    
    setMessages(prev => [...prev, { role: 'user', content: message }]);
    messageInput.value = '';
    
    try {
      const response = await fetch('http://localhost:5000/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json',
        },
        credentials: 'include',
        mode: 'cors',
        body: JSON.stringify({ message, name: personName }),
      });
      
      if (!response.ok) throw new Error('Failed to get response');
      
      const data = await response.json();
      setMessages(prev => [...prev, { role: 'assistant', content: data.response }]);
      
      // Automatically generate speech for AI response
      await generateSpeech(data.response);
    } catch (error) {
      console.error('Error sending message:', error);
    }
  };

  return (
    <div className="min-h-screen bg-gray-100 p-4">
      <div className="max-w-4xl mx-auto">
        <h1 className="text-3xl font-bold text-center mb-8">AI Clone Chat</h1>
        
        {!isCloneReady ? (
          <form onSubmit={handleCreateClone} className="bg-white p-6 rounded-lg shadow-md">
            <div className="mb-4">
              <label htmlFor="personName" className="block text-sm font-medium text-gray-700 mb-2">
                Enter Person&apos;s Name
              </label>
              <input
                type="text"
                id="personName"
                value={personName}
                onChange={(e) => setPersonName(e.target.value)}
                className="w-full px-4 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="e.g. Elon Musk"
                required
              />
            </div>
            <button
              type="submit"
              disabled={isLoading}
              className="w-full bg-blue-500 text-white py-2 px-4 rounded-md hover:bg-blue-600 disabled:bg-blue-300"
            >
              {isLoading ? 'Creating Clone...' : 'Create AI Clone'}
            </button>
          </form>
        ) : (
          <div className="bg-white p-6 rounded-lg shadow-md">
            <div className="mb-4">
              <h2 className="text-xl font-semibold mb-4">Chat with {personName}&apos;s AI Clone</h2>
              <div className="h-96 overflow-y-auto mb-4 p-4 border rounded-md">
                {messages.map((msg, index) => (
                  <div
                    key={index}
                    className={`mb-4 ${
                      msg.role === 'user' ? 'text-right' : 'text-left'
                    }`}
                  >
                    <div
                      className={`inline-block p-3 rounded-lg ${
                        msg.role === 'user'
                          ? 'bg-blue-500 text-white'
                          : 'bg-gray-200 text-gray-800'
                      }`}
                    >
                      {msg.content}
                      {msg.role === 'assistant' && (
                        <button
                          onClick={() => generateSpeech(msg.content)}
                          disabled={isSpeaking}
                          className="ml-2 text-sm text-blue-600 hover:text-blue-800 disabled:text-gray-400"
                        >
                          {isSpeaking ? '🔊 Speaking...' : '🔈 Play'}
                        </button>
                      )}
                    </div>
                  </div>
                ))}
              </div>
              <form onSubmit={handleSendMessage} className="flex gap-2">
                <input
                  type="text"
                  name="message"
                  className="flex-1 px-4 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="Type your message..."
                  required
                />
                <button
                  type="submit"
                  className="bg-blue-500 text-white py-2 px-6 rounded-md hover:bg-blue-600"
                >
                  Send
                </button>
              </form>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
