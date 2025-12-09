import type React from "react";

export const FeatureSection = () => {
  const feature = [
    {
      title: "No Encryption",
      description: "Standard data transmission without encryption",
    },
    {
      title: "QKD + AES BB84",
      description:
        "Quantum Key Distribution with BB84 protocol and AES-256-GCM encryption",
    },
    {
      title: "Standard AES-256-GCM",
      description: "Military-grade AES-256-GCM encryption",
    },
    {
      title: "QRNG + PQC",
      description:
        "Quantum Random Number Generation with Post-Quantum Cryptography",
    },
  ];

  return (
    <div className="flex flex-col justify-center items-center mt-10">
      <div className="flex flex-col justify-center items-center">
        <Heading>Features & Encryptions</Heading>
        <p className="text-center text-muted-slate text-sm max-w-2xl mt-2 leading-relaxed">
          Unbreakable security with Quantum Key Distribution (QKD) and
          AES-256-GCM encryption for ultimate privacy.
        </p>{" "}
      </div>

      <div className="relative grid  grid-cols-2 gap-4 p-4 mt-10 ">
        {feature.map((item, index) => (
          <Box key={index} className="relative">
            <h3 className="text-xl font-semibold mb-2 text-dark-slate">
              {item.title}
            </h3>
            <p className="text-soft-slate text-sm text-center">
              {item.description}
            </p>
          </Box>
        ))}

        <div className="absolute w-px h-40 bg-linear-to-t from-transparent via-gray-200 to-transparent left-[50%] top-[20%]"></div>
        <div className="absolute h-px w-50 bg-linear-to-r from-transparent via-gray-200 to-transparent top-[50%] left-[40%] "></div>
      </div>
    </div>
  );
};

export const Heading = ({
  children,
  className,
}: {
  children: React.ReactNode;
  className?: string;
}) => {
  return (
    <p
      className={`${className} text-4xl bg-linear-to-r from-deep-navy via-tech-blue to-deep-navy bg-clip-text text-transparent font-bold`}
    >
      {children}
    </p>
  );
};

export const Box = ({
  children,
  className,
}: {
  children: React.ReactNode;
  className?: String;
}) => {
  return (
    <div
      className={`${className} px-10 py-6 flex flex-col justify-center items-center hover:scale-103 hover:shadow-2xl shadow-gray-200/50 duration-200 transition-all bg-white rounded-xl border border-gray-100 hover:border-gray-200`}
    >
      {children}
    </div>
  );
};
