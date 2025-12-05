import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import {
  Monitor,
  Type,
  MousePointer2,
  Link,
  MoveHorizontal,
  Smile,
  ArrowUpDown,
  AlignJustify,
  PauseCircle,
  MessageCircle,
  RotateCcw,
  RefreshCw,
  X,
  Accessibility,
} from 'lucide-react';

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Separator } from '@/components/ui/separator';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';

interface ToolButtonProps {
  icon: React.ElementType;
  label: string;
  active: boolean;
  onClick: () => void;
}

function ToolButton({ icon: Icon, label, active, onClick }: ToolButtonProps) {
  return (
    <motion.button
      whileHover={{ scale: 1.02 }}
      whileTap={{ scale: 0.98 }}
      onClick={onClick}
      className={`relative flex flex-col items-center justify-center p-3 rounded-xl border transition-all duration-200 h-24 w-full ${active
          ? 'bg-violet-50 dark:bg-violet-900/30 border-violet-300 dark:border-violet-700 text-violet-700 dark:text-violet-300 shadow-sm'
          : 'bg-white dark:bg-slate-800 border-border hover:bg-slate-50 dark:hover:bg-slate-700/50 text-foreground'
        }`}
    >
      <div
        className={`mb-2 p-2 rounded-lg ${active
            ? 'bg-violet-100 dark:bg-violet-800 text-violet-600 dark:text-violet-300'
            : 'bg-slate-100 dark:bg-slate-700 text-muted-foreground'
          }`}
      >
        <Icon size={20} strokeWidth={2} />
      </div>
      <span className="text-xs text-center font-medium leading-tight">{label}</span>
      {active && (
        <motion.div
          initial={{ scale: 0 }}
          animate={{ scale: 1 }}
          className="absolute top-2 right-2 h-2 w-2 rounded-full bg-violet-500"
        />
      )}
    </motion.button>
  );
}

export default function AccessibilityTools() {
  const [isOpen, setIsOpen] = useState(false);
  const [settings, setSettings] = useState({
    contrast: false,
    biggerFont: false,
    cursor: false,
    highlightLinks: false,
    textSpacing: false,
    friendlyFont: false,
    lineHeight: false,
    textAlign: false,
    videos: false,
    tooltips: false,
  });

  useEffect(() => {
    const root = document.documentElement;

    if (settings.contrast) root.classList.add('access-high-contrast');
    else root.classList.remove('access-high-contrast');

    if (settings.biggerFont) root.classList.add('access-big-font');
    else root.classList.remove('access-big-font');

    if (settings.cursor) root.classList.add('access-big-cursor');
    else root.classList.remove('access-big-cursor');

    if (settings.highlightLinks) root.classList.add('access-links-highlight');
    else root.classList.remove('access-links-highlight');

    if (settings.textSpacing) root.classList.add('access-text-spacing');
    else root.classList.remove('access-text-spacing');

    if (settings.friendlyFont) root.classList.add('access-friendly-font');
    else root.classList.remove('access-friendly-font');

    if (settings.lineHeight) root.classList.add('access-line-height');
    else root.classList.remove('access-line-height');

    if (settings.textAlign) root.classList.add('access-text-align-justify');
    else root.classList.remove('access-text-align-justify');
  }, [settings]);

  const toggleSetting = (key: keyof typeof settings) => {
    setSettings((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  const resetSettings = () => {
    setSettings({
      contrast: false,
      biggerFont: false,
      cursor: false,
      highlightLinks: false,
      textSpacing: false,
      friendlyFont: false,
      lineHeight: false,
      textAlign: false,
      videos: false,
      tooltips: false,
    });
  };

  const reloadPage = () => {
    window.location.reload();
  };

  const activeCount = Object.values(settings).filter(Boolean).length;

  return (
    <TooltipProvider>
      <AnimatePresence>
        {!isOpen && (
          <motion.div
            initial={{ scale: 0, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            exit={{ scale: 0, opacity: 0 }}
            className="fixed bottom-6 right-6 z-50"
          >
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  onClick={() => setIsOpen(true)}
                  size="lg"
                  className="h-14 w-14 rounded-full bg-gradient-to-br from-violet-500 to-indigo-600 hover:from-violet-600 hover:to-indigo-700 shadow-lg shadow-violet-500/30 hover:shadow-xl hover:shadow-violet-500/40 transition-all duration-300"
                >
                  <Accessibility className="h-6 w-6" />
                  {activeCount > 0 && (
                    <span className="absolute -top-1 -right-1 h-5 w-5 rounded-full bg-emerald-500 text-[10px] font-bold flex items-center justify-center text-white ring-2 ring-white dark:ring-slate-900">
                      {activeCount}
                    </span>
                  )}
                </Button>
              </TooltipTrigger>
              <TooltipContent side="left">
                <p>Accessibility Tools</p>
              </TooltipContent>
            </Tooltip>
          </motion.div>
        )}
      </AnimatePresence>

      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0, x: 100, scale: 0.95 }}
            animate={{ opacity: 1, x: 0, scale: 1 }}
            exit={{ opacity: 0, x: 100, scale: 0.95 }}
            transition={{ type: 'spring', damping: 25, stiffness: 300 }}
            className="fixed top-20 right-6 z-50 w-80"
          >
            <Card className="shadow-2xl border-0 bg-white/95 dark:bg-slate-900/95 backdrop-blur-xl overflow-hidden">
              <CardHeader className="bg-gradient-to-r from-violet-500 to-indigo-600 text-white p-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="h-10 w-10 rounded-xl bg-white/20 flex items-center justify-center">
                      <Accessibility className="h-5 w-5" />
                    </div>
                    <div>
                      <CardTitle className="text-lg font-bold">Accessibility</CardTitle>
                      <p className="text-xs text-white/70">
                        {activeCount} {activeCount === 1 ? 'tool' : 'tools'} active
                      </p>
                    </div>
                  </div>
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={() => setIsOpen(false)}
                    className="text-white hover:bg-white/20 h-8 w-8"
                  >
                    <X className="h-4 w-4" />
                  </Button>
                </div>
              </CardHeader>

              <CardContent className="p-3">
                <div className="grid grid-cols-2 gap-2">
                  <ToolButton icon={Monitor} label="High Contrast" active={settings.contrast} onClick={() => toggleSetting('contrast')} />
                  <ToolButton icon={Type} label="Bigger Font" active={settings.biggerFont} onClick={() => toggleSetting('biggerFont')} />
                  <ToolButton icon={MousePointer2} label="Big Cursor" active={settings.cursor} onClick={() => toggleSetting('cursor')} />
                  <ToolButton icon={Link} label="Highlight Links" active={settings.highlightLinks} onClick={() => toggleSetting('highlightLinks')} />
                  <ToolButton icon={MoveHorizontal} label="Text Spacing" active={settings.textSpacing} onClick={() => toggleSetting('textSpacing')} />
                  <ToolButton icon={Smile} label="Friendly Font" active={settings.friendlyFont} onClick={() => toggleSetting('friendlyFont')} />
                  <ToolButton icon={ArrowUpDown} label="Line Height" active={settings.lineHeight} onClick={() => toggleSetting('lineHeight')} />
                  <ToolButton icon={AlignJustify} label="Text Align" active={settings.textAlign} onClick={() => toggleSetting('textAlign')} />
                  <ToolButton icon={PauseCircle} label="Pause Videos" active={settings.videos} onClick={() => toggleSetting('videos')} />
                  <ToolButton icon={MessageCircle} label="Tooltips" active={settings.tooltips} onClick={() => toggleSetting('tooltips')} />
                </div>

                <Separator className="my-3" />

                <div className="grid grid-cols-2 gap-2">
                  <Button variant="outline" onClick={resetSettings} className="flex items-center gap-2">
                    <RotateCcw className="h-4 w-4" />
                    Reset All
                  </Button>
                  <Button variant="outline" onClick={reloadPage} className="flex items-center gap-2">
                    <RefreshCw className="h-4 w-4" />
                    Reload
                  </Button>
                </div>
              </CardContent>
            </Card>
          </motion.div>
        )}
      </AnimatePresence>
    </TooltipProvider>
  );
}
