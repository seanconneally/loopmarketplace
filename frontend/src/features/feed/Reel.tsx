import { flushSignals, registerSampler, signalGeneration, signal } from './signals';
import { listingSummary } from '../listing/categories';
import { useEffect, useRef, useState } from 'react';
import Hls from 'hls.js';
import { Link, useLocation } from 'react-router-dom';
import { Bookmark, MapPin, MessageCircle, Pause, Play, Volume2, VolumeX } from 'lucide-react';
import { euros, type Listing } from '../../api/client';
import { useAuth } from '../../shared/Auth';

export function Reel({
  listing,
  nearby,
  onActive,
  onSave,
  onMessage,
  saving = false,
}: {
  listing: Listing;
  nearby: boolean;
  onActive: () => void;
  onSave: () => void;
  onMessage: () => void;
  saving?: boolean;
}) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const hlsRef = useRef<Hls | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const auth = useAuth();
  const location = useLocation();
  const isOwner = auth.user?.id === listing.seller.id;
  const [visible, setVisible] = useState(false);
  const [muted, setMuted] = useState(true);
  const [paused, setPaused] = useState(false);
  const [progress, setProgress] = useState(0);
  const [failed, setFailed] = useState(false);
  const activeCallback = useRef(onActive);
  activeCallback.current = onActive;

  useEffect(() => {
    const element = containerRef.current;
    if (!element) return;
    const observer = new IntersectionObserver(
      (entries) => {
        const active = entries[0].isIntersecting;
        setVisible(active);
        if (active) activeCallback.current();
      },
      { threshold: 0.65 },
    );
    observer.observe(element);
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    const video = videoRef.current;
    if (!video || !listing.playback_url || !nearby) return;
    let hls: Hls | undefined;
    if (listing.playback_url.includes('.m3u8') && Hls.isSupported()) {
      hls = new Hls({
        startLevel: 0,
        maxBufferLength: visible ? 15 : 3,
        maxMaxBufferLength: visible ? 30 : 3,
        capLevelToPlayerSize: true,
      });
      hls.loadSource(listing.playback_url);
      hls.attachMedia(video);
      hlsRef.current = hls;
      hls.on(Hls.Events.ERROR, (_event, data) => {
        if (data.fatal) setFailed(true);
      });
    } else video.src = listing.playback_url;
    return () => {
      hls?.destroy();
      hlsRef.current = null;
      video.pause();
      video.removeAttribute('src');
      video.load();
    };
    // Visibility changes must not recreate the current decoder; nearby controls its lifetime.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [listing.playback_url, nearby]);

  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;
    if (hlsRef.current) {
      hlsRef.current.config.maxBufferLength = visible ? 15 : 3;
      hlsRef.current.config.maxMaxBufferLength = visible ? 30 : 3;
    }
    if (visible && !paused) void video.play().catch(() => setPaused(true));
    else video.pause();
  }, [visible, paused, nearby]);

  useEffect(() => {
    if (!visible || !auth.user?.analytics_consent) return;
    const userId = auth.user.id;
    let lastReported = -1;
    const generation = signalGeneration();
    let watched = 0;
    let sampledAt = performance.now();
    let mediaTime = videoRef.current?.currentTime || 0;
    let started = false;
    const sample = window.setInterval(() => {
      const now = performance.now();
      const video = videoRef.current;
      if (
        video &&
        !video.paused &&
        video.readyState >= 3 &&
        document.visibilityState === 'visible'
      ) {
        const elapsed = (now - sampledAt) / 1000;
        const advance =
          video.currentTime >= mediaTime
            ? video.currentTime - mediaTime
            : Math.max(0, (video.duration || 0) - mediaTime + video.currentTime);
        const actual = Math.min(elapsed, Math.max(0, advance));
        watched += actual;
        started ||= actual > 0;
      }
      mediaTime = video?.currentTime || 0;
      sampledAt = now;
    }, 250);
    signal(userId, listing.id, 'impression', 1);
    const collect = () => {
      if (generation !== signalGeneration()) return;
      const duration = videoRef.current?.duration || listing.duration || 0;
      if (started && Number.isFinite(duration) && duration > 0 && watched > lastReported) {
        signal(userId, listing.id, 'completion', Math.min(1, watched / duration));
        const replays = Math.min(2, Math.max(0, watched / duration - 1));
        if (replays > 0) signal(userId, listing.id, 'replay', replays);
        lastReported = watched;
      }
    };
    const unregister = registerSampler(collect);
    const flush = () => {
      collect();
      void flushSignals();
    };
    const interval = window.setInterval(flush, 10000);
    const visibility = () => {
      if (document.visibilityState === 'hidden') flush();
    };
    document.addEventListener('visibilitychange', visibility);
    return () => {
      window.clearInterval(interval);
      window.clearInterval(sample);
      document.removeEventListener('visibilitychange', visibility);
      unregister();
      if (generation === signalGeneration())
        signal(userId, listing.id, 'watch', Math.min(60, watched));
      flush();
    };
  }, [visible, auth.user?.id, auth.user?.analytics_consent, listing.id, listing.duration]);

  return (
    <div className="reel" ref={containerRef}>
      <video
        ref={videoRef}
        poster={listing.poster_url || undefined}
        muted={muted}
        loop
        playsInline
        preload={nearby ? 'metadata' : 'none'}
        onError={() => setFailed(true)}
        onTimeUpdate={(event) => {
          const video = event.currentTarget;
          setProgress(video.duration ? (video.currentTime / video.duration) * 100 : 0);
        }}
      />
      <div className="reel-shade" />
      <div className="reel-top">
        <span className="reel-badge">
          <span className="live-dot" />
          {listing.seller.dealer_verified ? 'VERIFIED DEALER' : 'LOCAL SELLER'}
        </span>
        <span className="clip-time">{Math.round(listing.duration || 15)}s tour</span>
      </div>
      <button
        className="video-toggle"
        aria-label={paused ? 'Play video' : 'Pause video'}
        onClick={() => setPaused(!paused)}
      >
        {paused ? <Play size={30} fill="currentColor" /> : <Pause size={25} />}
      </button>
      {failed && (
        <div className="video-status">Video unavailable. You can still view the listing.</div>
      )}
      <div className="reel-actions">
        <button
          onClick={onSave}
          aria-label={listing.saved ? 'Unsave listing' : 'Save listing'}
          className={listing.saved ? 'is-saved' : ''}
          disabled={saving}
        >
          <Bookmark size={22} fill={listing.saved ? 'currentColor' : 'none'} />
          <span>Save</span>
        </button>
        <button
          onClick={onMessage}
          disabled={!isOwner && listing.status !== 'live'}
          aria-label={isOwner ? 'Manage advert' : 'Message seller'}
        >
          <MessageCircle size={22} />
          <span>{isOwner ? 'Manage' : listing.status === 'sold' ? 'Sold' : 'Chat'}</span>
        </button>
        <button
          onClick={() => setMuted(!muted)}
          disabled={!listing.has_audio}
          aria-label={
            !listing.has_audio ? 'Video has no audio' : muted ? 'Unmute video' : 'Mute video'
          }
        >
          {muted ? <VolumeX size={21} /> : <Volume2 size={21} />}
          {!listing.has_audio && <span>No audio</span>}
        </button>
      </div>
      <div className="reel-caption">
        <div className="location-tag">
          <MapPin size={13} />
          {listing.area}, Dublin
        </div>
        <h2>
          <Link
            to={`/listings/${listing.id}`}
            state={{ from: location.pathname + location.search }}
            aria-label={`View ${listing.title}`}
          >
            {listing.title}
          </Link>
        </h2>
        <p>{listingSummary(listing)}</p>
        <div className="reel-price">
          {euros(listing.price_cents)}
          <span>See it. Love it. Make it yours.</span>
        </div>
      </div>
      <div className="video-progress">
        <span style={{ width: `${progress}%` }} />
      </div>
    </div>
  );
}
