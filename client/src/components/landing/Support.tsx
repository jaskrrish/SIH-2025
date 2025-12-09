import { Heading } from "./FeatureSection";
import apple from "../../assets/email/apple.png";
import google from "../../assets/email/google.png";
import outlook from "../../assets/email/outlook.png";
import yahoo from "../../assets/email/yahoo.png";

export const Support = () => {
  return (
    <div className="flex flex-col justify-between items-center mt-10">
      <Heading className="mb-4">Emails Support</Heading>

      <div className="flex flex-wrap justify-center gap-8 mt-8 mb-16">
        <div className="size-10 bg-white rounded-full overflow-hidden shadow-md shadow-gray-200">
          <img src={apple} alt="Apple" />
        </div>
        <div className="size-10 rounded-full overflow-hidden">
          <img src={google} alt="Google" />
        </div>
        <div className="size-10 rounded-full overflow-hidden">
          <img src={outlook} alt="Outlook" />
        </div>
        <div className="size-10 rounded-full overflow-hidden">
          <img src={yahoo} alt="Yahoo" />
        </div>
      </div>
    </div>
  );
};
