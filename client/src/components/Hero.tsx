import bg from "../assets/page.jpg";
import { Button } from "./ui/Button";

import DecryptedText from "../components/ui/DecryptedText";
export const Hero = () => {
  return (
    <div className="flex flex-col justify-center items-center gap-15">
      <p className="bg-gradient-to-r from-deep-navy via-tech-blue to-deep-navy bg-clip-text text-transparent max-w-2xl text-5xl  text-center mx-auto font-bold">
        Secure Your Communications with{" "}
        <span>
          <DecryptedText
            text="Quantam Encryption"
            animateOn="view"
            revealDirection="center"
            speed={70}
            maxIterations={20}
            className="text-accent"
          />
        </span>
      </p>

      <p className="max-w-2xl mx-auto text-center  text-muted-slate ">
        Experience unbreakable security powered by{" "}
        <span className="text-deep-navy font-semibold">
          Quantum Key Distribution (QKD)
        </span>{" "}
        technology. Your messages are protected by the laws of physics.
      </p>

      <Button>Start Mailing</Button>

      <div className="mask-b-from-55% relative  mt-8 overflow-hidden px-2">
        <div className="inset-shadow-2xs ring-background  bg-background relative mx-auto max-w-5xl overflow-hidden rounded-2xl border border-gray-200 p-4 shadow-lg shadow-gray-200/50 ring-1">
          <img
            className="bg-background aspect-15/8 relative block rounded-2xl"
            src={bg}
            alt="app screen"
            width="2700"
            height="1440"
          />
        </div>
      </div>
    </div>
  );
};
