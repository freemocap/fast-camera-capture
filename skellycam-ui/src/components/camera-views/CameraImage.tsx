import {Box, Typography} from "@mui/material";
import React from "react";

interface CameraImageProps {
    cameraId: string;
    base64Image: string;
    showAnnotation: boolean;
}

export const CameraImage = ({cameraId, base64Image, showAnnotation}: CameraImageProps) => {
    return (
        <Box
            key={cameraId}
            sx={{
                position: "relative",
                // display: "flex",
                // justifyContent: "center",
                // alignItems: "center",
                // flexBasis: "calc(50% - 5px)",
                // margin: "1px",
                // width: "100%",
                // height: "auto",
                boxSizing: "border-box",
                border: "1px solid #a0a",
            }}
        >
            <img
                src={`data:image/jpeg;base64,${base64Image}`}
                alt={`Camera ${cameraId}`}
                style={{
                    // width: "100%",
                    // height: "auto",
                    // maxHeight: "100%",
                    // objectFit: "contain"
                }}
            />
            {showAnnotation && (
                <Typography
                    variant="caption"
                    sx={{
                        position: "absolute",
                        bottom: 8,
                        left: 8,
                        color: "white",
                        backgroundColor: "rgba(0, 0, 0, 0.75)",
                        padding: "2px 4px",
                        borderRadius: "4px"
                    }}
                >
                    Camera {cameraId}
                </Typography>
            )}
        </Box>
    );
};
